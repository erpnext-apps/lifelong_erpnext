from typing import Literal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt, nowdate, nowtime

from erpnext.stock.utils import get_or_make_bin, get_stock_balance
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
	validate_stock_reservation_settings,
	get_sre_reserved_qty_details_for_voucher,
	get_available_qty_to_reserve
)

def create_stock_reservation_entries_for_so_items(
	sales_order: object,
	items_details: list[dict] | None = None,
	from_voucher_type: Literal["Pick List", "Purchase Receipt"] = None,
	notify=True,
) -> None:
	"""Creates Stock Reservation Entries for Sales Order Items."""

	from erpnext.selling.doctype.sales_order.sales_order import get_unreserved_qty

	if not from_voucher_type and (
		sales_order.get("_action") == "submit"
		and sales_order.set_warehouse
		and cint(frappe.get_cached_value("Warehouse", sales_order.set_warehouse, "is_group"))
	):
		return frappe.msgprint(
			_("Stock cannot be reserved in the group warehouse {0}.").format(
				frappe.bold(sales_order.set_warehouse)
			)
		)

	validate_stock_reservation_settings(sales_order)

	allow_partial_reservation = frappe.db.get_single_value("Stock Settings", "allow_partial_reservation")

	items = []
	if items_details:
		for item in items_details:
			so_item = frappe.get_doc("Sales Order Item", item.get("sales_order_item"))
			so_item.warehouse = item.get("warehouse")
			so_item.qty_to_reserve = (
				flt(item.get("qty_to_reserve"))
				if from_voucher_type in ["Pick List", "Purchase Receipt"]
				else (
					flt(item.get("qty_to_reserve"))
					* (flt(item.get("conversion_factor")) or flt(so_item.conversion_factor) or 1)
				)
			)
			so_item.from_voucher_no = item.get("from_voucher_no")
			so_item.from_voucher_detail_no = item.get("from_voucher_detail_no")
			so_item.serial_and_batch_bundle = item.get("serial_and_batch_bundle")

			items.append(so_item)

	sre_count = 0
	reserved_qty_details = get_sre_reserved_qty_details_for_voucher("Sales Order", sales_order.name)

	for item in items if items_details else sales_order.get("items"):
		# Skip if `Reserved Stock` is not checked for the item.
		if not item.get("reserve_stock"):
			continue

		# Stock should be reserved from the Pick List if has Picked Qty.
		if not from_voucher_type == "Pick List" and flt(item.picked_qty) > 0:
			frappe.throw(
				_("Row #{0}: Item {1} has been picked, please reserve stock from the Pick List.").format(
					item.idx, frappe.bold(item.item_code)
				)
			)

		is_stock_item, has_serial_no, has_batch_no = frappe.get_cached_value(
			"Item", item.item_code, ["is_stock_item", "has_serial_no", "has_batch_no"]
		)

		# Skip if Non-Stock Item.
		if not is_stock_item:
			if not from_voucher_type:
				frappe.msgprint(
					_("Row #{0}: Stock cannot be reserved for a non-stock Item {1}").format(
						item.idx, frappe.bold(item.item_code)
					),
					title=_("Stock Reservation"),
					indicator="yellow",
				)

			item.db_set("reserve_stock", 0)
			continue

		# Skip if Group Warehouse.
		if frappe.get_cached_value("Warehouse", item.warehouse, "is_group"):
			frappe.msgprint(
				_("Row #{0}: Stock cannot be reserved in group warehouse {1}.").format(
					item.idx, frappe.bold(item.warehouse)
				),
				title=_("Stock Reservation"),
				indicator="yellow",
			)
			continue

		unreserved_qty = get_unreserved_qty(item, reserved_qty_details)

		# Stock is already reserved for the item, notify the user and skip the item.
		if unreserved_qty <= 0:
			if not from_voucher_type:
				frappe.msgprint(
					_("Row #{0}: Stock is already reserved for the Item {1}.").format(
						item.idx, frappe.bold(item.item_code)
					),
					title=_("Stock Reservation"),
					indicator="yellow",
				)

			continue

		available_qty_to_reserve = get_available_qty_to_reserve(item.item_code, item.warehouse)

		# No stock available to reserve, notify the user and skip the item.
		if available_qty_to_reserve <= 0:
			frappe.msgprint(
				_("Row #{0}: Stock not available to reserve for the Item {1} in Warehouse {2}.").format(
					item.idx, frappe.bold(item.item_code), frappe.bold(item.warehouse)
				),
				title=_("Stock Reservation"),
				indicator="orange",
			)
			continue

		# The quantity which can be reserved.
		qty_to_be_reserved = min(unreserved_qty, available_qty_to_reserve)

		if hasattr(item, "qty_to_reserve"):
			if item.qty_to_reserve <= 0:
				frappe.msgprint(
					_("Row #{0}: Quantity to reserve for the Item {1} should be greater than 0.").format(
						item.idx, frappe.bold(item.item_code)
					),
					title=_("Stock Reservation"),
					indicator="orange",
				)
				continue
			else:
				qty_to_be_reserved = min(qty_to_be_reserved, item.qty_to_reserve)

		# Partial Reservation
		if qty_to_be_reserved < unreserved_qty:
			if not from_voucher_type and (
				not item.get("qty_to_reserve") or qty_to_be_reserved < flt(item.get("qty_to_reserve"))
			):
				msg = _("Row #{0}: Only {1} available to reserve for the Item {2}").format(
					item.idx,
					frappe.bold(str(qty_to_be_reserved / item.conversion_factor) + " " + item.uom),
					frappe.bold(item.item_code),
				)
				frappe.msgprint(msg, title=_("Stock Reservation"), indicator="orange")

			# Skip the item if `Partial Reservation` is disabled in the Stock Settings.
			if not allow_partial_reservation:
				if qty_to_be_reserved == flt(item.get("qty_to_reserve")):
					msg = _(
						"Enable Allow Partial Reservation in the Stock Settings to reserve partial stock."
					)
					frappe.msgprint(msg, title=_("Partial Stock Reservation"), indicator="yellow")

				continue
		doctype = (
			"Stock Reserve Entry"
			if frappe.db.get_single_value("Stock Settings", "custom_reservation_type")
			== "Custom"
			else "Stock Reservation Entry"
		)
		sre = frappe.new_doc(doctype)

		sre.item_code = item.item_code
		sre.warehouse = item.warehouse
		sre.has_serial_no = has_serial_no
		sre.has_batch_no = has_batch_no
		sre.voucher_type = sales_order.doctype
		sre.voucher_no = sales_order.name
		sre.voucher_detail_no = item.name
		sre.available_qty = available_qty_to_reserve
		sre.voucher_qty = item.stock_qty
		sre.reserved_qty = qty_to_be_reserved
		sre.company = sales_order.company
		sre.stock_uom = item.stock_uom
		sre.project = sales_order.project

		if from_voucher_type:
			sre.from_voucher_type = from_voucher_type
			sre.from_voucher_no = item.from_voucher_no
			sre.from_voucher_detail_no = item.from_voucher_detail_no

		if item.get("serial_and_batch_bundle"):
			sbb = frappe.get_doc("Serial and Batch Bundle", item.serial_and_batch_bundle)
			sre.reservation_based_on = "Serial and Batch"

			index, picked_qty = 0, 0
			while index < len(sbb.entries) and picked_qty < qty_to_be_reserved:
				entry = sbb.entries[index]
				qty = 1 if has_serial_no else min(abs(entry.qty), qty_to_be_reserved - picked_qty)

				sre.append(
					"sb_entries",
					{
						"serial_no": entry.serial_no,
						"batch_no": entry.batch_no,
						"qty": qty,
						"warehouse": entry.warehouse,
					},
				)

				index += 1
				picked_qty += qty

		sre.save()
		sre.submit()

		sre_count += 1

	if sre_count and notify:
		frappe.msgprint(_("Stock Reservation Entries Created"), alert=True, indicator="green")
