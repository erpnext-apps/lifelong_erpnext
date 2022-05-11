# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

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
			name, creation, naming_series
		FROM
			`tab{document_details.doctype}`
		WHERE
			{condition}
	""", as_dict=1)

	canceled_documents = frappe.db.sql(f"""
		SELECT
			COUNT(name) as total_number, naming_series
		FROM
			`tab{document_details.doctype}`
		WHERE
			{condition} AND docstatus = 2
		GROUP BY
			naming_series
	""", as_dict=1) or {}

	if canceled_documents:
		canceled_documents = {row.naming_series: row.total_number for row in canceled_documents}

	naming_series_data = {}
	for item in data:
		if item.naming_series not in naming_series_data:
			naming_series_data.setdefault(item.naming_series, {})

		names = naming_series_data.get(item.naming_series)
		names[item.name] = item.creation

	res = []
	for naming_series, name_data in naming_series_data.items():
		if not name_data:
			continue

		sorted_names = sorted(name_data.items(), key=lambda x: x[1])
		res.append(frappe._dict({
			"naming_series": naming_series,
			"nature_of_document": nature_of_document,
			"from_serial_no": sorted_names[0][0],
			"to_serial_no": sorted_names[len(sorted_names) - 1][0],
			"total_number": len(name_data),
			"canceled": canceled_documents.get(naming_series)
		}))

	return res