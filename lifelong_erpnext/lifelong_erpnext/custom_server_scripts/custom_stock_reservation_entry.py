from typing import Literal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt

def create_stock_reservation_entries_for_so_items(
	sales_order: object,
	items_details: list[dict] | None = None,
	from_voucher_type: Literal["Pick List", "Purchase Receipt"] = None,
	notify=True,
) -> None:
	"""Creates Stock Reservation Entries for Sales Order Items."""

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

	items_to_loop = items if items_details else sales_order.get("items")

	for item in items_to_loop:
		is_stock_item, has_serial_no, has_batch_no = frappe.get_cached_value(
			"Item", item.item_code, ["is_stock_item", "has_serial_no", "has_batch_no"]
		)
		
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
		sre.available_qty = item.qty_to_reserve
		sre.voucher_qty = item.stock_qty
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
			while index < len(sbb.entries) and picked_qty < item.qty_to_reserve:
				entry = sbb.entries[index]
				qty = 1 if has_serial_no else min(abs(entry.qty), item.qty_to_reserve - picked_qty)

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
