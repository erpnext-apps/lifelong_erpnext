# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _, bold
from frappe.model.document import Document
from .utils import validate_rack_zone_warehouse

class Shelf(Document):
	def validate(self):
		self.validate_unique_shelf()
		if not self.is_new():
			self.check_stock_exsts()
		validate_rack_zone_warehouse(self)
	def check_stock_exsts(self):
		warehouse = frappe.db.get_value('Shelf', self.name, 'warehouse')

		if self.warehouse != warehouse:
			sle_exists = frappe.db.get_value('Stock Ledger Entry',
				{'warehouse': warehouse, 'is_cancelled': 0}, 'name')

			if sle_exists:
				frappe.throw(_(f'The stock ledgers exists against the warehouse {bold(warehouse)}'))
	

	def get_short_code(value):
		import re
		"""
		Converts 'Rack 1' -> 'R1', 'Zone 1' -> 'Z1'.
		Falls back to the original value if it doesn't match the '<Word> <Number>' pattern.
		"""
		if not value:
			return value

		match = re.match(r"^([A-Za-z]+)\s*(\d+)$", value.strip())
		if match:
			letter = match.group(1)[0].upper()
			number = match.group(2)
			return f"{letter}{number}"

		return value


	def autoname(self):
		if not self.shelf_name:
			frappe.throw("Shelf Name is required")

		if not self.rack:
			frappe.throw("Rack is required")

		if not self.zone:
			frappe.throw("Zone is required")

		clean_rack = frappe.db.get_value("Rack", self.rack, "rack_name")
		clean_zone = frappe.db.get_value("Zone", self.zone, "zone_name")
		clean_shelf = self.shelf_name

		if not clean_rack or not clean_zone:
			frappe.throw("Could not retrieve names for Rack or Zone from the database.")

		short_rack = self.get_short_code(clean_rack)
		short_zone = self.get_short_code(clean_zone)

		# FINAL CLEAN NAME: shelf_name_R#_Z#
		self.name = f"{clean_shelf}_{short_rack}_{short_zone}"

	

	

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