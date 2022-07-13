# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import execute as _execute

def execute(filters=None):
	columns, data, message, chart, report_summary, skip_total_row = _execute(filters)
	columns.extend([{
		"label": _("Batch"),
		"fieldname": "batch",
		"fieldtype": "Link",
		"options": "Batch",
		"width": 120,
		},
		{
		"label": _("Valuation Rate"),
		"fieldname": "valuation_rate",
		"fieldtype": "Float",
		"width": 120,
		}
	])
	for d in data:
		if d["delivery_note"]:
			batch_value = frappe.db.get_value(
				"Stock Ledger Entry",
				{"voucher_type": "Delivery Note", "voucher_no": d["delivery_note"], "item_code": d["item_code"]},
				["valuation_rate", "batch_no"],
				as_dict = 1
				)
			d["valuation_rate"] = batch_value.valuation_rate
			d["batch"] = batch_value.batch_no
	return columns, data, message, chart, report_summary, skip_total_row
