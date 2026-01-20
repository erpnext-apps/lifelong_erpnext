import frappe
from frappe import _
from collections import OrderedDict
from frappe.utils import cint, floor, flt, today

from erpnext.stock.doctype.pick_list.pick_list import (PickList,
	get_available_item_locations_for_serial_and_batched_item, get_available_item_locations_for_serialized_item,
	get_available_item_locations_for_other_item)

from lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_utils import get_available_batches

class CustomPickList(PickList):
	def aggregate_item_qty(self):
		locations = self.get("locations")
		self.item_count_map = {}
		# aggregate qty for same item
		item_map = OrderedDict()
		for item in locations:
			if not item.item_code:
				frappe.throw("Row #{0}: Item Code is Mandatory".format(item.idx))
			item_code = item.item_code
			reference = item.sales_order_item or item.material_request_item
			key = (item_code, item.uom, reference)

			item.idx = None
			item.name = None

			if item_map.get(key):
				item_map[key].qty += item.qty
				item_map[key].stock_qty += item.stock_qty
			else:
				item_map[key] = item

			# maintain count of each item (useful to limit get query)
			self.item_count_map.setdefault(item_code, 0)
			self.item_count_map[item_code] += item.stock_qty

		return item_map.values()

	@frappe.whitelist()
	def set_item_locations(self, save=False):
		if self.select_manually:
			return

		self.validate_for_qty()
		items = self.aggregate_item_qty()
		self.item_location_map = frappe._dict()

		from_warehouses = []
		if self.child_warehouse:
			from_warehouses = [self.child_warehouse]

		if self.parent_warehouse and not self.child_warehouse:
			from_warehouses = frappe.db.get_descendants('Warehouse', self.parent_warehouse)

		# Create replica before resetting, to handle empty table on update after submit.
		locations_replica  = self.get('locations')

		# reset
		self.delete_key('locations')
		for item_doc in items:
			item_code = item_doc.item_code

			self.item_location_map.setdefault(item_code,
				get_available_item_locations(item_code, from_warehouses, self.item_count_map.get(item_code), self.company, item_doc))

			locations = get_items_with_location_and_quantity(item_doc, self.item_location_map, self.docstatus)

			item_doc.idx = None
			item_doc.name = None

			for row in locations:
				row.update({
					'picked_qty': row.stock_qty
				})
				location = item_doc.as_dict()
				location.update(row)
				self.append('locations', location)

		# If table is empty on update after submit, set stock_qty, picked_qty to 0 so that indicator is red
		# and give feedback to the user. This is to avoid empty Pick Lists.
		if not self.get('locations') and self.docstatus == 1:
			for location in locations_replica:
				location.stock_qty = 0
				location.picked_qty = 0
				self.append('locations', location)
			frappe.msgprint(_("Please Restock Items and Update the Pick List to continue. To discontinue, cancel the Pick List."),
				 title=_("Out of Stock"), indicator="red")

		if save:
			self.save()

	def validate_picked_items(self):
		for item in self.locations:
			if self.scan_mode and item.picked_qty < item.stock_qty:
				frappe.throw(
					_(
						"Row {0} picked quantity is less than the required quantity, additional {1} {2} required."
					).format(item.idx, item.stock_qty - item.picked_qty, item.stock_uom),
					title=_("Pick List Incomplete"),
				)

			if not self.scan_mode and item.picked_qty == 0:
				# if the user has not entered any picked qty, set it to stock_qty, before submit
				# item.picked_qty = item.stock_qty Don't set picked qty, it will be updated manually
				pass
	
	@frappe.whitelist()
	def create_stock_reservation_entries(self, notify=True) -> None:
		"""Creates Stock Reservation Entries for Sales Order Items against Pick List."""

		so_items_details_map = {}
		for location in self.locations:
			if location.warehouse and location.sales_order and location.sales_order_item and (flt(location.stock_qty) - flt(location.stock_reserved_qty) - flt(location.custom_transfered_qty)) > 0 and location.serial_and_batch_bundle:
				item_details = {
					"sales_order_item": location.sales_order_item,
					"item_code": location.item_code,
					"warehouse": location.warehouse,
					"qty_to_reserve": (flt(location.stock_qty) - flt(location.stock_reserved_qty) - flt(location.custom_transfered_qty)), # use stock_qty instead of picked_qty
					"from_voucher_no": location.parent,
					"from_voucher_detail_no": location.name,
					"serial_and_batch_bundle": location.serial_and_batch_bundle,
				}
				so_items_details_map.setdefault(location.sales_order, []).append(item_details)

		if so_items_details_map:
			from lifelong_erpnext.lifelong_erpnext.custom_server_scripts.custom_stock_reservation_entry import create_stock_reservation_entries_for_so_items
			for so, items_details in so_items_details_map.items():
				so_doc = frappe.get_doc("Sales Order", so)
				if frappe.db.get_single_value("Stock Settings", "custom_reservation_type") == "Standard":
					so_doc.create_stock_reservation_entries(
						items_details=items_details,
						from_voucher_type="Pick List",
						notify=notify,
					)
				else:
					create_stock_reservation_entries_for_so_items(
						so_doc,
						items_details=items_details,
						from_voucher_type="Pick List",
						notify=notify,
					)
				
	def on_update_after_submit(self) -> None:
		return # Ignore this method, Pick List will be updated after submit
		if self.has_reserved_stock():
			msg = _(
				"The Pick List having Stock Reservation Entries cannot be updated. If you need to make changes, we recommend canceling the existing Stock Reservation Entries before updating the Pick List."
			)
			frappe.throw(msg)

	def validate_sales_order(self):
		"""Raises an exception if the `Sales Order` has reserved stock."""
		return # Validation not required
		if self.purpose != "Delivery":
			return

		so_list = set(location.sales_order for location in self.locations if location.sales_order)

		if so_list:
			for so in so_list:
				so_doc = frappe.get_doc("Sales Order", so)
				for item in so_doc.items:
					if item.stock_reserved_qty > 0:
						frappe.throw(
							_(
								"Cannot create a pick list for Sales Order {0} because it has reserved stock. Please unreserve the stock in order to create a pick list."
							).format(frappe.bold(so))
						)

def get_available_item_locations(item_code, from_warehouses, required_qty, company, item_doc, ignore_validation=False):
	locations = []
	has_serial_no  = frappe.get_cached_value('Item', item_code, 'has_serial_no')
	has_batch_no = frappe.get_cached_value('Item', item_code, 'has_batch_no')

	if has_batch_no and has_serial_no:
		locations = get_available_item_locations_for_serial_and_batched_item(item_code, from_warehouses, required_qty, company)
	elif has_serial_no:
		locations = get_available_item_locations_for_serialized_item(item_code, from_warehouses, required_qty, company)
	elif has_batch_no:
		locations = get_available_item_locations_for_batched_item(item_code, from_warehouses, required_qty, company, item_doc)
	else:
		locations = get_available_item_locations_for_other_item(item_code, from_warehouses, required_qty, company)

	total_qty_available = sum(location.get('qty') for location in locations)

	# remaining_qty = required_qty - total_qty_available

	# if remaining_qty > 0 and not ignore_validation:
	# 	frappe.msgprint(_('{0} units of Item {1} is not available.')
	# 		.format(remaining_qty, frappe.get_desk_link('Item', item_code)),
	# 		title=_("Insufficient Stock"))

	return locations

def get_available_item_locations_for_batched_item(item_code, from_warehouses, required_qty, company, item_doc):
	batch_locations = get_available_batches(item_code, from_warehouses, company, doctype="Pick List")

	return batch_locations

def get_items_with_location_and_quantity(item_doc, item_location_map, docstatus):
	available_locations = item_location_map.get(item_doc.item_code)
	locations = []

	# if stock qty is zero on submitted entry, show positive remaining qty to recalculate in case of restock.
	remaining_stock_qty = item_doc.qty if (docstatus == 1 and item_doc.stock_qty == 0) else item_doc.stock_qty

	while remaining_stock_qty > 0 and available_locations:
		item_location = available_locations.pop(0)
		item_location = frappe._dict(item_location)

		stock_qty = remaining_stock_qty if item_location.qty >= remaining_stock_qty else item_location.qty
		qty = stock_qty / (item_doc.conversion_factor or 1)

		uom_must_be_whole_number = frappe.get_cached_value('UOM', item_doc.uom, 'must_be_whole_number')
		if uom_must_be_whole_number:
			qty = floor(qty)
			stock_qty = qty * item_doc.conversion_factor
			if not stock_qty: break

		serial_nos = None
		if item_location.serial_no:
			serial_nos = '\n'.join(item_location.serial_no[0: cint(stock_qty)])

		locations.append(frappe._dict({
			'qty': qty,
			'stock_qty': stock_qty,
			'warehouse': item_location.warehouse,
			'serial_no': serial_nos,
			'batch_no': item_location.batch_no,
			'shelf': item_location.shelf
		}))

		remaining_stock_qty -= stock_qty

		qty_diff = item_location.qty - stock_qty
		# if extra quantity is available push current warehouse to available locations
		if qty_diff > 0:
			item_location.qty = qty_diff
			if item_location.serial_no:
				# set remaining serial numbers
				item_location.serial_no = item_location.serial_no[-int(qty_diff):]
			available_locations = [item_location] + available_locations

	# update available locations for the item
	item_location_map[item_doc.item_code] = available_locations
	return locations


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def warehouse_query(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("parent_warehouse"):
		lft, rgt = frappe.db.get_value("Warehouse", filters.get("parent_warehouse"), ["lft", "rgt"])

		return frappe.get_all(
			"Warehouse",
			filters = {"lft": [">", lft], "rgt": ["<", rgt],
				"company": filters.get("company"), "name": ("like", f"%{txt}%"), "is_group": 0},
			fields = ["name"],
			limit_start = start,
			limit_page_length=page_len,
			as_list=1
		)
