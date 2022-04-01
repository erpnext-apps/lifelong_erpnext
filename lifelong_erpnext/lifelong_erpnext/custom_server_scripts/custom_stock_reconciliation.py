import frappe
from frappe import _, msgprint
from frappe.utils import cint, cstr, flt

from erpnext.stock.doctype.batch.batch import get_batch_qty
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.utils import get_stock_balance

from lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_utils import get_available_batches
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import StockReconciliation

class CustomStockReconciliation(StockReconciliation):
	def remove_items_with_no_change(self):
		"""Remove items if qty or rate is not changed"""
		self.difference_amount = 0.0
		def _changed(item):
			item_dict = get_stock_balance_for(item.item_code, item.warehouse,
				self.posting_date, self.posting_time, batch_no=item.batch_no,
				shelf=item.shelf, company=self.company, with_valuation_rate=True)

			if ((item.qty is None or item.qty==item_dict.get("qty")) and
				(item.valuation_rate is None or item.valuation_rate==item_dict.get("rate")) and
				(not item.serial_no or (item.serial_no == item_dict.get("serial_nos")) )):
				return False
			else:
				# set default as current rates
				if item.qty is None:
					item.qty = item_dict.get("qty")

				if item.valuation_rate is None:
					item.valuation_rate = item_dict.get("rate")

				if item_dict.get("serial_nos"):
					item.current_serial_no = item_dict.get("serial_nos")
					if self.purpose == "Stock Reconciliation" and not item.serial_no:
						item.serial_no = item.current_serial_no

				item.current_qty = item_dict.get("qty")
				item.current_valuation_rate = item_dict.get("rate")
				self.difference_amount += (flt(item.qty, item.precision("qty")) * \
					flt(item.valuation_rate or item_dict.get("rate"), item.precision("valuation_rate")) \
					- flt(item_dict.get("qty"), item.precision("qty")) * flt(item_dict.get("rate"), item.precision("valuation_rate")))
				return True

		items = list(filter(lambda d: _changed(d), self.items))

		if not items:
			frappe.throw(_("None of the items have any change in quantity or value."),
				EmptyStockReconciliationItemsError)

		elif len(items) != len(self.items):
			self.items = items
			for i, item in enumerate(self.items):
				item.idx = i + 1
			frappe.msgprint(_("Removed items with no change in quantity or value."))


	def validate_data(self):
		def _get_msg(row_num, msg):
			return _("Row # {0}:").format(row_num+1) + " " + msg

		self.validation_messages = []
		item_warehouse_combinations = []

		default_currency = frappe.db.get_default("currency")

		for row_num, row in enumerate(self.items):
			# find duplicates
			key = [row.item_code, row.warehouse]
			for field in ['serial_no', 'batch_no', 'shelf']:
				if row.get(field):
					key.append(row.get(field))

			if key in item_warehouse_combinations:
				self.validation_messages.append(_get_msg(row_num, _("Duplicate entry")))
			else:
				item_warehouse_combinations.append(key)

			self.validate_item(row.item_code, row)

			# validate warehouse
			if not frappe.db.get_value("Warehouse", row.warehouse):
				self.validation_messages.append(_get_msg(row_num, _("Warehouse not found in the system")))

			# if both not specified
			if row.qty in ["", None] and row.valuation_rate in ["", None]:
				self.validation_messages.append(_get_msg(row_num,
					_("Please specify either Quantity or Valuation Rate or both")))

			# do not allow negative quantity
			if flt(row.qty) < 0:
				self.validation_messages.append(_get_msg(row_num,
					_("Negative Quantity is not allowed")))

			# do not allow negative valuation
			if flt(row.valuation_rate) < 0:
				self.validation_messages.append(_get_msg(row_num,
					_("Negative Valuation Rate is not allowed")))

			if row.qty and row.valuation_rate in ["", None]:
				row.valuation_rate = get_stock_balance(row.item_code, row.warehouse,
							self.posting_date, self.posting_time, with_valuation_rate=True)[1]
				if not row.valuation_rate:
					# try if there is a buying price list in default currency
					buying_rate = frappe.db.get_value("Item Price", {"item_code": row.item_code,
						"buying": 1, "currency": default_currency}, "price_list_rate")
					if buying_rate:
						row.valuation_rate = buying_rate

					else:
						# get valuation rate from Item
						row.valuation_rate = frappe.get_value('Item', row.item_code, 'valuation_rate')

		# throw all validation messages
		if self.validation_messages:
			for msg in self.validation_messages:
				msgprint(msg)

			raise frappe.ValidationError(self.validation_messages)

	def get_sle_for_serialized_items(self, row, sl_entries):
		from erpnext.stock.stock_ledger import get_previous_sle

		serial_nos = get_serial_nos(row.serial_no)


		# To issue existing serial nos
		if row.current_qty and (row.current_serial_no or row.batch_no):
			args = self.get_sle_for_items(row)
			args.update({
				"actual_qty": -1 * row.current_qty,
				"serial_no": row.current_serial_no,
				"batch_no": row.batch_no,
				"shelf": row.shelf,
				"valuation_rate": row.current_valuation_rate
			})

			if row.current_serial_no:
				args.update({
					"qty_after_transaction": 0,
				})

			sl_entries.append(args)

		qty_after_transaction = 0
		for serial_no in serial_nos:
			args = self.get_sle_for_items(row, [serial_no])

			previous_sle = get_previous_sle({
				"item_code": row.item_code,
				"posting_date": self.posting_date,
				"posting_time": self.posting_time,
				"serial_no": serial_no,
				"shelf": row.shelf
			})

			if previous_sle and row.warehouse != previous_sle.get("warehouse"):
				# If serial no exists in different warehouse

				warehouse = previous_sle.get("warehouse", '') or row.warehouse

				if not qty_after_transaction:
					qty_after_transaction = get_stock_balance(row.item_code,
						warehouse, self.posting_date, self.posting_time)

				qty_after_transaction -= 1

				new_args = args.copy()
				new_args.update({
					"actual_qty": -1,
					"qty_after_transaction": qty_after_transaction,
					"warehouse": warehouse,
					"valuation_rate": previous_sle.get("valuation_rate")
				})

				sl_entries.append(new_args)

		if row.qty:
			args = self.get_sle_for_items(row)

			args.update({
				"actual_qty": row.qty,
				"incoming_rate": row.valuation_rate,
				"shelf": row.shelf,
				"valuation_rate": row.valuation_rate
			})

			sl_entries.append(args)

		if serial_nos == get_serial_nos(row.current_serial_no):
			# update valuation rate
			self.update_valuation_rate_for_serial_nos(row, serial_nos)

	def get_sle_for_items(self, row, serial_nos=None):
		"""Insert Stock Ledger Entries"""

		if not serial_nos and row.serial_no:
			serial_nos = get_serial_nos(row.serial_no)

		data = frappe._dict({
			"doctype": "Stock Ledger Entry",
			"item_code": row.item_code,
			"warehouse": row.warehouse,
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"voucher_detail_no": row.name,
			"company": self.company,
			"stock_uom": frappe.db.get_value("Item", row.item_code, "stock_uom"),
			"is_cancelled": 1 if self.docstatus == 2 else 0,
			"serial_no": '\n'.join(serial_nos) if serial_nos else '',
			"batch_no": row.batch_no,
			"shelf": row.shelf,
			"valuation_rate": flt(row.valuation_rate, row.precision("valuation_rate"))
		})

		if not row.batch_no:
			data.qty_after_transaction = flt(row.qty, row.precision("qty"))

		if self.docstatus == 2 and not row.batch_no:
			if row.current_qty:
				data.actual_qty = -1 * row.current_qty
				data.qty_after_transaction = flt(row.current_qty)
				data.previous_qty_after_transaction = flt(row.qty)
				data.valuation_rate = flt(row.current_valuation_rate)
				data.stock_value = data.qty_after_transaction * data.valuation_rate
				data.stock_value_difference = -1 * flt(row.amount_difference)
			else:
				data.actual_qty = row.qty
				data.qty_after_transaction = 0.0
				data.valuation_rate = flt(row.valuation_rate)
				data.stock_value_difference = -1 * flt(row.amount_difference)

		return data

@frappe.whitelist()
def get_stock_balance_for(*args, **kargs):
	frappe.has_permission("Stock Reconciliation", "write", throw = True)

	item_code, warehouse, posting_date, posting_time = args
	kargs = frappe._dict(kargs)

	item_dict = frappe.db.get_value("Item", item_code,
		["has_serial_no", "has_batch_no"], as_dict=1)

	if not item_dict:
		# In cases of data upload to Items table
		msg = _("Item {} does not exist.").format(item_code)
		frappe.throw(msg, title=_("Missing"))

	if kargs.shelf:
		if kargs.batch_no:
			data = get_available_batches(item_code, warehouse,
				kargs.company, batch_no=kargs.batch_no, shelf=kargs.shelf)
			if data:
				return data[0]
		else:
			return frappe._dict()

	serial_nos = ""
	with_serial_no = True if item_dict.get("has_serial_no") else False
	data = get_stock_balance(item_code, warehouse, posting_date, posting_time,
		with_valuation_rate=kargs.with_valuation_rate, with_serial_no=with_serial_no)

	if with_serial_no:
		qty, rate, serial_nos = data
	else:
		qty, rate = data

	if item_dict.get("has_batch_no"):
		qty = get_batch_qty(kargs.batch_no, warehouse, posting_date=posting_date, posting_time=posting_time) or 0

	return {
		'qty': qty,
		'rate': rate,
		'serial_nos': serial_nos
	}