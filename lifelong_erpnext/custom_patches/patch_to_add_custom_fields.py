import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
	frappe.reload_doc('lifelong_erpnext', 'doctype', 'shelf')

	df = dict(fieldname='shelf', insert_after='warehouse',
		label='Shelf', fieldtype='Link', options='Shelf')

	for doctype in ['Putaway Rule', 'Stock Ledger Entry',
		'Purchase Receipt Item', 'Stock Entry Detail', 'Delivery Note Item']:
		create_custom_field(doctype, df)

	create_custom_field('Putaway Rule',
		dict(fieldname='volumetric_weight', label='Volumetric Weight',
			fieldtype='Float', insert_after='conversion_factor'))

	create_custom_field('Warehouse',
		dict(fieldname='has_shelf', label='Has Shelf',
			fieldtype='Check', insert_after='disabled'))

