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
		if not self.rack:
			frappe.throw("Rack is required")

		zone = frappe.db.get_value("Rack", self.rack, "zone")

		if not zone:
			frappe.throw(f"Zone not found for Rack {self.rack}")

		if not self.warehouse:
			frappe.throw("Warehouse is required")

		if not self.shelf_name:
			frappe.throw("Shelf Name is required")

		self.name = (
			f"{self.shelf_name}-"
			f"{self.rack}-"
			f"{zone}-"
			f"{self.warehouse}"
		)

	
	def validate_unique_shelf(self):
		zone = frappe.db.get_value("Rack", self.rack, "zone")

		existing = frappe.db.exists(
			"Shelf",
			{
				"warehouse": self.warehouse,
				"rack": self.rack,
				"shelf_name": self.shelf_name,
				"name": ["!=", self.name]
			}
		)

		if existing:
			frappe.throw(
				f"Shelf '{self.shelf_name}' already exists in "
				f"Rack '{self.rack}', Zone '{zone}', "
				f"Warehouse '{self.warehouse}'"
			)