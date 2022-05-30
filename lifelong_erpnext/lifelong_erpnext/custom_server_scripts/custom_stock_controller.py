import frappe

from collections import defaultdict
from frappe.utils import flt, nowdate, nowtime, cstr
from frappe import _
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_putaway_rule import apply_putaway_rule

class CustomStockController(PurchaseReceipt):
	def before_validate(self):
		if self.get("items") and self.apply_putaway_rule and not self.get("is_return"):
			apply_putaway_rule(self.doctype, self.get("items"), self.company)

	def validate_putaway_capacity(self):
		# if over receipt is attempted while 'apply putaway rule' is disabled
		# and if rule was applied on the transaction, validate it.
		valid_doctype = self.doctype in ("Purchase Receipt", "Stock Entry", "Purchase Invoice",
			"Stock Reconciliation")

		if self.doctype == "Purchase Invoice" and self.get("update_stock") == 0:
			valid_doctype = False

		if valid_doctype:
			rule_map = defaultdict(dict)
			for item in self.get("items"):
				warehouse_field = "t_warehouse" if self.doctype == "Stock Entry" else "warehouse"
				rule = frappe.db.get_value("Putaway Rule",
					{
						"item_code": item.get("item_code"),
						"warehouse": item.get(warehouse_field),
						"shelf": item.get("shelf")
					},
					["name", "disable"], as_dict=True)
				if rule:
					if rule.get("disabled"): continue # dont validate for disabled rule

					if self.doctype == "Stock Reconciliation":
						stock_qty = flt(item.qty)
					else:
						stock_qty = flt(item.transfer_qty) if self.doctype == "Stock Entry" else flt(item.stock_qty)

					rule_name = rule.get("name")
					if not rule_map[rule_name]:
						rule_map[rule_name]["warehouse"] = item.get(warehouse_field)
						rule_map[rule_name]["item"] = item.get("item_code")
						rule_map[rule_name]["qty_put"] = 0
						rule_map[rule_name]["capacity"] = get_available_putaway_capacity(rule_name,
							self.posting_date, self.posting_time)
					rule_map[rule_name]["qty_put"] += flt(stock_qty)

			for rule, values in rule_map.items():
				if flt(values["qty_put"]) > flt(values["capacity"]):
					message = self.prepare_over_receipt_message(rule, values)
					frappe.throw(msg=message, title=_("Over Receipt"))

	def make_batches(self, warehouse_field):
		'''Create batches if required. Called before submit'''
		pass

class CustomStockEntry(StockEntry):
	def before_validate(self):
		if self.get("items") and self.apply_putaway_rule and not self.get("is_return"):
			apply_putaway_rule(self.doctype, self.get("items"), self.company)

	def validate_warehouse(self):
		"""perform various (sometimes conditional) validations on warehouse"""

		source_mandatory = ["Material Issue", "Material Transfer", "Send to Subcontractor", "Material Transfer for Manufacture",
			"Material Consumption for Manufacture"]

		target_mandatory = ["Material Receipt", "Material Transfer", "Send to Subcontractor",
			"Material Transfer for Manufacture"]

		validate_for_manufacture = any([d.bom_no for d in self.get("items")])

		if self.purpose in source_mandatory and self.purpose not in target_mandatory:
			self.to_warehouse = None
			for d in self.get('items'):
				d.t_warehouse = None
		elif self.purpose in target_mandatory and self.purpose not in source_mandatory:
			self.from_warehouse = None
			for d in self.get('items'):
				d.s_warehouse = None

		for d in self.get('items'):
			if not d.s_warehouse and not d.t_warehouse:
				d.s_warehouse = self.from_warehouse
				d.t_warehouse = self.to_warehouse

			if self.purpose in source_mandatory and not d.s_warehouse:
				if self.from_warehouse:
					d.s_warehouse = self.from_warehouse
				else:
					frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if self.purpose in target_mandatory and not d.t_warehouse:
				if self.to_warehouse:
					d.t_warehouse = self.to_warehouse
				else:
					frappe.throw(_("Target warehouse is mandatory for row {0}").format(d.idx))

			if self.purpose == "Manufacture":
				if validate_for_manufacture:
					if d.is_finished_item or d.is_scrap_item or d.is_process_loss:
						d.s_warehouse = None
						if not d.t_warehouse:
							frappe.throw(_("Target warehouse is mandatory for row {0}").format(d.idx))
					else:
						d.t_warehouse = None
						if not d.s_warehouse:
							frappe.throw(_("Source warehouse is mandatory for row {0}").format(d.idx))

			if cstr(d.s_warehouse) == cstr(d.t_warehouse) and d.shelf == d.target_shelf:
				frappe.throw(_("Source and target shelf cannot be same for row {0}").format(d.idx))

			if not (d.s_warehouse or d.t_warehouse):
				frappe.throw(_("Atleast one warehouse is mandatory"))

	def validate_putaway_capacity(self):
		# if over receipt is attempted while 'apply putaway rule' is disabled
		# and if rule was applied on the transaction, validate it.
		valid_doctype = self.doctype in ("Purchase Receipt", "Stock Entry", "Purchase Invoice",
			"Stock Reconciliation")

		if self.doctype == "Purchase Invoice" and self.get("update_stock") == 0:
			valid_doctype = False

		if valid_doctype:
			rule_map = defaultdict(dict)
			for item in self.get("items"):
				warehouse_field = "t_warehouse" if self.doctype == "Stock Entry" else "warehouse"
				rule = frappe.db.get_value("Putaway Rule",
					{
						"item_code": item.get("item_code"),
						"warehouse": item.get(warehouse_field),
						"shelf": item.get("shelf")
					},
					["name", "disable"], as_dict=True)
				if rule:
					if rule.get("disabled"): continue # dont validate for disabled rule

					if self.doctype == "Stock Reconciliation":
						stock_qty = flt(item.qty)
					else:
						stock_qty = flt(item.transfer_qty) if self.doctype == "Stock Entry" else flt(item.stock_qty)

					rule_name = rule.get("name")
					if not rule_map[rule_name]:
						rule_map[rule_name]["warehouse"] = item.get(warehouse_field)
						rule_map[rule_name]["item"] = item.get("item_code")
						rule_map[rule_name]["qty_put"] = 0
						rule_map[rule_name]["capacity"] = get_available_putaway_capacity(rule_name,
							self.posting_date, self.posting_time)
					rule_map[rule_name]["qty_put"] += flt(stock_qty)

			for rule, values in rule_map.items():
				if flt(values["qty_put"]) > flt(values["capacity"]):
					message = self.prepare_over_receipt_message(rule, values)
					frappe.throw(msg=message, title=_("Over Receipt"))


@frappe.whitelist()
def get_available_putaway_capacity(rule, posting_date=None, posting_time=None):
	from lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_utils import get_stock_balance
	stock_capacity, item_code, warehouse, shelf = frappe.db.get_value("Putaway Rule", rule,
		["stock_capacity", "item_code", "warehouse", "shelf"])
	balance_qty = get_stock_balance({
		'item_code': item_code,
		'warehouse': warehouse,
		'shelf': shelf,
		'posting_date': posting_date or nowdate(),
		'posting_time': posting_time or nowtime()
	}, "<=", "desc", "limit 1")

	free_space = flt(stock_capacity) - flt(balance_qty)
	return free_space if free_space > 0 else 0

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def address_query(doctype, txt, searchfield, start, page_len, filters):
	from frappe.desk.reportview import get_match_cond

	link_doctype = filters.pop('link_doctype')
	link_name = filters.pop('link_name')

	condition = ""
	meta = frappe.get_meta("Address")
	for fieldname, value in filters.items():
		if meta.get_field(fieldname) or fieldname in frappe.db.DEFAULT_COLUMNS:
			condition += " and {field}={value}".format(
				field=fieldname,
				value=frappe.db.escape(value))

	searchfields = meta.get_search_fields()

	if searchfield and (meta.get_field(searchfield)\
				or searchfield in frappe.db.DEFAULT_COLUMNS):
		searchfields.append(searchfield)

	search_condition = ''
	for field in searchfields:
		if search_condition == '':
			search_condition += '`tabAddress`.`{field}` like %(txt)s'.format(field=field)
		else:
			search_condition += ' or `tabAddress`.`{field}` like %(txt)s'.format(field=field)

	return frappe.db.sql("""select
			`tabAddress`.name, `tabAddress`.city, `tabAddress`.country
		from
			`tabAddress`, `tabDynamic Link`
		where
			`tabDynamic Link`.parent = `tabAddress`.name and
			`tabDynamic Link`.parenttype = 'Address' and
			`tabDynamic Link`.link_doctype = %(link_doctype)s and
			`tabDynamic Link`.link_name = %(link_name)s and
			ifnull(`tabAddress`.disabled, 0) = 0 and
			({search_condition})
			{mcond} {condition}
		order by
			if(locate(%(_txt)s, `tabAddress`.name), locate(%(_txt)s, `tabAddress`.name), 99999),
			`tabAddress`.idx desc, `tabAddress`.name
		limit %(start)s, %(page_len)s """.format(
			mcond=get_match_cond(doctype),
			key=searchfield,
			search_condition = search_condition,
			condition=condition or ""), {
			'txt': '%' + txt + '%',
			'_txt': txt.replace("%", ""),
			'start': start,
			'page_len': page_len,
			'link_name': link_name,
			'link_doctype': link_doctype
		})