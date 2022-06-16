# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt
from frappe.model.naming import parse_naming_series
from collections import defaultdict

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_columns(filters):
	return [
		{
			"fieldname": "nature_of_document",
			"label": _("Nature of Document"),
			"fieldtype": "Data",
			"width": 300
		},
		{
			"fieldname": "naming_series",
			"label": _("Series"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "from_serial_no",
			"label": _("Serial Number From"),
			"fieldtype": "Data",
			"width": 160
		},
		{
			"fieldname": "to_serial_no",
			"label": _("Serial Number To"),
			"fieldtype": "Data",
			"width": 160
		},
		{
			"fieldname": "total_number",
			"label": _("Total Submitted Number"),
			"fieldtype": "Int",
			"width": 180
		},
		{
			"fieldname": "canceled",
			"label": _("Canceled Number"),
			"fieldtype": "Int",
			"width": 160
		}
	]

def get_data(filters) -> list:
	data = []
	bank_accounts = frappe.db.sql_list(""" SELECT
		name from `tabAccount` where account_type = 'Bank' """)

	bank_accounts = tuple(bank_accounts) + ("", )

	document_mapper = {
		"Invoices for outward supply": {
			"doctype": "Sales Invoice"
		},
		"Invoices for inward supply": {
			"doctype": "Purchase Invoice",
			"condition": "gst_category != 'Unregistered'"
		},
		"Invoices for inward supply from unregistered person": {
			"doctype": "Purchase Invoice",
			"condition": "gst_category = 'Unregistered'"
		},
		"Debit Note": {
			"doctype": "Purchase Invoice",
			"condition": "is_return = 1"
		},
		"Credit Note": {
			"doctype": "Sales Invoice",
			"condition": "is_return = 1"
		},
		"Receipt Voucher": {
			"doctype": "Payment Entry",
			"condition": "payment_type =  'Receive'"
		},
		"Payment Voucher": {
			"doctype": "Payment Entry",
			"condition": "payment_type =  'Pay'"
		},
		"Receipt Voucher (JV)": {
			"doctype": "Journal Entry",
			"condition": (f"""name in (
				SELECT distinct parent from `tabJournal Entry Account`
					where account in {bank_accounts} and debit > 0 and credit = 0)
				and voucher_type not in ('Contra Entry')
			""")
		},
		"Payment Voucher (JV)": {
			"doctype": "Journal Entry",
			"condition": (f"""name in (
				SELECT distinct parent from `tabJournal Entry Account`
					where account in {bank_accounts} and debit = 0 and credit > 0)
				and voucher_type not in ('Contra Entry')
			""")
		}
	}

	for nature_of_document, document_details in document_mapper.items():
		document_details = frappe._dict(document_details)
		data.extend(get_document_summary(filters, document_details, nature_of_document))

	return data

def get_document_summary(filters, document_details, nature_of_document):
	condition = (f"""company = {frappe.db.escape(filters.company)}
		AND posting_date BETWEEN '{filters.from_date}' AND '{filters.to_date}'
		AND naming_series IS NOT NULL AND docstatus > 0 """)

	if document_details.condition:
		condition += f" AND {document_details.condition}"

	for field in ["company_gstin", "company_address"]:
		if filters.get(field):
			if document_details.doctype == "Purchase Invoice":
				condition += f" AND shipping_address = '{filters.get(field)}'"
			else:
				condition += f" AND {field} = '{filters.get(field)}'"

	data = frappe.db.sql(f"""
		SELECT
			*
		FROM
			`tab{document_details.doctype}`
		WHERE
			{condition}
	""", as_dict=1)

	naming_series_data = {}

	for item in data:
		naming_series = parse_naming_series(item.naming_series.replace('#', ''), doc=item)

		if naming_series not in naming_series_data:
			naming_series_data.setdefault(naming_series, {
				"canceled_count": 0,
				"tot_count": 0,
				"document_names": {}
			})

		names = naming_series_data.get(naming_series)
		if item.docstatus == 2:
			names["canceled_count"] += 1

		names["document_names"][item.name] = item.creation
		names["tot_count"] += 1

	res = []
	for naming_series, name_data in naming_series_data.items():
		if not name_data:
			continue

		sorted_names = sorted(name_data["document_names"].items(), key=lambda x: x[1])
		if sorted_names and len(sorted_names[0]) > 0:
			res.append(frappe._dict({
				"naming_series": naming_series,
				"nature_of_document": nature_of_document,
				"from_serial_no": sorted_names[0][0],
				"to_serial_no": sorted_names[len(sorted_names) - 1][0],
				"total_number": name_data.get("tot_count"),
				"canceled": name_data.get("canceled_count")
			}))

	return res