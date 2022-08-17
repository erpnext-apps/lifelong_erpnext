# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import datetime
from frappe.utils import cint, flt, getdate, get_datetime, nowdate


def execute(filters=None):
	if not filters: filters = {}

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_batch_map(filters, float_precision)

	data = []

	iwb_map = sorted(iwb_map.items(), key= lambda x: (x[1].get('creation'), x[1].get('bal_qty')))
	for row in iwb_map:
		if row[1].bal_qty > 0.0:
			data.append(row[1])

	return columns, data


def get_columns(filters):
	"""return columns based on filters"""

	columns = [
		{
			'fieldname': 'item_code',
			'fieldtype': 'Link',
			'label': 'Item Code',
			'options': 'Item',
			'width': 120
		},
		{
			'fieldname': 'item_name',
			'fieldtype': 'Data',
			'label': 'Item Name',
			'width': 100
		},
		{
			'fieldname': 'stock_uom',
			'fieldtype': 'Link',
			'label': 'UOM',
			'options': 'UOM',
			'width': 60
		},
		{
			'fieldname': 'warehouse',
			'fieldtype': 'Link',
			'label': 'Warehouse',
			'options': 'Warehouse',
			'width': 100
		},
		{
			'fieldname': 'shelf',
			'fieldtype': 'Link',
			'label': 'Shelf',
			'options': 'Shelf',
			'width': 100
		},
		{
			'fieldname': 'batch_no',
			'fieldtype': 'Link',
			'label': 'Batch',
			'options': 'Batch',
			'width': 100
		},
		{
			'fieldname': 'opening_qty',
			'fieldtype': 'Float',
			'label': 'Opening Qty',
			'width': 120
		},
		{
			'fieldname': 'in_qty',
			'fieldtype': 'Float',
			'label': 'In Qty',
			'width': 100
		},
		{
			'fieldname': 'out_qty',
			'fieldtype': 'Float',
			'label': 'Out Qty',
			'width': 100
		},
		{
			'fieldname': 'bal_qty',
			'fieldtype': 'Float',
			'label': 'Balance Qty',
			'width': 100
		},
		{
			'fieldname': 'creation',
			'fieldtype': 'Datetime',
			'label': 'Creation',
			'width': 180
		},
		{
			'fieldname': 'valuation_rate',
			'fieldtype': 'Float',
			'label': 'Valuation Rate',
			'width': 180
		}
	]

	return columns


def get_conditions(filters):
	conditions = ""

	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if filters.get("to_date") and filters.get("posting_time"):
		conditions += f""" and timestamp(posting_date, posting_time)
			<= timestamp('{filters["to_date"]}', '{filters.get("posting_time")}')"""

	elif filters.get("to_date"):
		conditions += " and posting_date <= '%s'" % filters["to_date"]

	else:
		frappe.throw(_("'To Date' is required"))

	for field in ["item_code", "batch_no", "company", "shelf"]:
		if filters.get(field):
			conditions += " and {0} = {1}".format(field, frappe.db.escape(filters.get(field)))

	if filters.get('warehouse'):
		if isinstance(filters.get('warehouse'), str):
			conditions += f" and warehouse = {frappe.db.escape(filters.get('warehouse'))}"
		else:
			warehouses = filters.get('warehouse')
			if len(warehouses) == 1:
				warehouses.append("All")

			conditions += f" and warehouse in {tuple(warehouses)}"

	return conditions


# get all details
def get_stock_ledger_entries(filters):
	conditions = get_conditions(filters)
	shelf_type_cond = ""
	if filters.get("doctype") and filters.get("doctype") in ['Pick List', 'Delivery Note', 'Sales Invoice']:
		shelf_type_cond = " and sle.shelf in (select name from `tabShelf` where type = 'Sellable')"

	return frappe.db.sql(f"""
		SELECT
			sle.item_code, sle.batch_no, sle.warehouse, sle.posting_date,
			sum(sle.actual_qty) as qty, sle.shelf, DATE_FORMAT(batch.creation, '%Y-%m-%d %H:%i:%s') as creation,
			batch.item_name, batch.description, batch.stock_uom, sle.valuation_rate
		FROM
	 		`tabStock Ledger Entry` sle, `tabBatch` batch
		WHERE
			sle.is_cancelled = 0 and sle.docstatus < 2 and ifnull(sle.batch_no, '') != '' {conditions}
			and batch.name = sle.batch_no and IFNULL(batch.`expiry_date`, '2200-01-01') > '{nowdate()}'
			and sle.shelf is not null {shelf_type_cond}
		GROUP BY
			sle.voucher_no, sle.batch_no, sle.item_code, sle.warehouse, sle.shelf
		ORDER BY
			sle.item_code, sle.warehouse, batch.creation, qty""", as_dict=1)


def get_item_warehouse_batch_map(filters, float_precision):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	for d in sle:
		key = (d.item_code, d.warehouse, d.batch_no, d.shelf)

		iwb_map.setdefault(key, frappe._dict({
			"opening_qty": 0.0, "in_qty": 0.0, "out_qty": 0.0, "bal_qty": 0.0, "creation": get_datetime(d.creation),
			"item_code": d.item_code, "warehouse": d.warehouse, "batch_no": d.batch_no, "shelf": d.shelf,
			"item_name": d.item_name, "description": d.description, "stock_uom": d.stock_uom, "valuation_rate": d.valuation_rate
		}))

		qty_dict = iwb_map[key]
		if d.posting_date < from_date:
			qty_dict.opening_qty = flt(qty_dict.opening_qty, float_precision) \
				+ flt(d.qty, float_precision)
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(d.qty) > 0:
				qty_dict.in_qty = flt(qty_dict.in_qty, float_precision) + flt(d.qty, float_precision)
			else:
				qty_dict.out_qty = flt(qty_dict.out_qty, float_precision) \
					+ abs(flt(d.qty, float_precision))

		qty_dict.bal_qty = flt(qty_dict.bal_qty, float_precision) + flt(d.qty, float_precision)
		qty_dict.qty = qty_dict.bal_qty

	return iwb_map


def get_item_details(filters):
	item_map = {}
	for d in frappe.db.sql("select name, item_name, description, stock_uom from tabItem where has_batch_no = 1", as_dict=1):
		item_map.setdefault(d.name, d)

	return item_map
