import frappe

from collections import defaultdict
from frappe.utils import flt, nowdate, nowtime
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

class CustomStockEntry(StockEntry):
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