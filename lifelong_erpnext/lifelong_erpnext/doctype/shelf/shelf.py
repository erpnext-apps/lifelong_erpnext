# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _, bold
from frappe.model.document import Document

class Shelf(Document):
	def validate(self):
		if not self.is_new():
			self.check_stock_exsts()

	def check_stock_exsts(self):
		warehouse = frappe.db.get_value('Shelf', self.name, 'warehouse')

		if self.warehouse != warehouse:
			sle_exists = frappe.db.get_value('Stock Ledger Entry',
				{'warehouse': warehouse, 'is_cancelled': 0}, 'name')

			if sle_exists:
				frappe.throw(_(f'The stock ledgers exists against the warehouse {bold(warehouse)}'))