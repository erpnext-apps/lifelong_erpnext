# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _, bold
from frappe.model.document import Document

class Shelf(Document):
	def validate(self):
		self.validate_unique_shelf()
		if not self.is_new():
			self.check_stock_exsts()

	def check_stock_exsts(self):
		warehouse = frappe.db.get_value('Shelf', self.name, 'warehouse')

		if self.warehouse != warehouse:
			sle_exists = frappe.db.get_value('Stock Ledger Entry',
				{'warehouse': warehouse, 'is_cancelled': 0}, 'name')

			if sle_exists:
				frappe.throw(_(f'The stock ledgers exists against the warehouse {bold(warehouse)}'))
	
	def autoname(self):

		if not self.shelf_name:
			frappe.throw("Shelf Name is required")

		if not self.rack:
			frappe.throw("Rack is required")

		# Validate rack has zone (data integrity check)
		zone = frappe.get_cached_value("Rack", self.rack, "zone")

		if not zone:
			frappe.throw(f"Zone not set in Rack {self.rack}")

		if not self.warehouse:
			frappe.throw("Warehouse is required")

		# FINAL CLEAN NAME
		self.name = f"{self.shelf_name}-{self.rack}"

	

	def validate_unique_shelf(self):

		existing = frappe.db.exists(
			"Shelf",
			{
				"rack": self.rack,
				"shelf_name": self.shelf_name,
				"name": ["!=", self.name]
			}
		)

		if existing:
			frappe.throw(
				f"Shelf '{self.shelf_name}' already exists in Rack '{self.rack}'"
			)