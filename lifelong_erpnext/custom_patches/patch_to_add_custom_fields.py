import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field, create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute():
	frappe.reload_doc('lifelong_erpnext', 'doctype', 'shelf')

	df = dict(fieldname='shelf', insert_after='warehouse',
		label='Shelf', fieldtype='Link', options='Shelf', in_list_view=1)

	for doctype in ['Putaway Rule', 'Stock Ledger Entry', 'Sales Invoice Item', 'Purchase Invoice Item',
		'Purchase Receipt Item', 'Stock Entry Detail', 'Delivery Note Item', 'Pick List Item',
		'Stock Reconciliation Item']:
		if doctype in ['Sales Invoice Item', 'Purchase Invoice Item']:
			df['depends_on'] = 'eval:parent.update_stock == 1'

		if doctype in ['Stock Ledger Entry']:
			df['read_only'] = 1

		create_custom_field(doctype, df)

	create_custom_field('Putaway Rule',
		dict(fieldname='volumetric_weight', label='Volumetric Weight',
			fieldtype='Float', insert_after='conversion_factor'))

	create_custom_field('Purchase Receipt Item',
		dict(fieldname='from_shelf', label='From Shelf',
			read_only = 1, fieldtype='Link', options='Shelf', insert_after='shelf',
			depends_on='eval:parent.is_internal_supplier || doc.from_warehouse'))

	create_custom_field('Delivery Note Item',
		dict(fieldname='target_shelf', label='Target Shelf',
			fieldtype='Link', options='Shelf', insert_after='target_warehouse',
			depends_on='eval:parent.is_internal_customer || doc.target_warehouse'))

	create_custom_field('Delivery Note',
		dict(fieldname='target_shelf', label='Target Shelf',
			fieldtype='Link', options='Shelf', insert_after='set_target_warehouse',
			depends_on='eval:parent.is_internal_customer || doc.set_target_warehouse'))

	create_custom_field('Stock Entry Detail',
		dict(fieldname='target_shelf', label='Target Shelf',
			fieldtype='Link', options='Shelf', insert_after='shelf',
			depends_on='eval:parent.purpose == "Material Transfer"'))

	create_custom_field('Stock Entry',
		dict(fieldname='target_shelf', label='Target Shelf',
			fieldtype='Link', options='Shelf', insert_after='target_warehouse',
			depends_on='eval:doc.purpose == "Material Transfer"'))

	create_custom_field('Warehouse',
		dict(fieldname='has_shelf', label='Has Shelf',
			fieldtype='Check', insert_after='disabled'))

	for doctype in ['Sales Invoice Item', 'Delivery Note Item', 'Stock Entry Detail']:
		create_custom_fields({
			doctype: [
				dict(fieldname='edit_batch', label='Edit Batch',
					fieldtype='Button', in_list_view=1, insert_after='shelf'),
				dict(fieldname='actual_shelf_batch_qty', label='Actual Batch Qty',
					fieldtype='Float', hidden=1, insert_after='edit_batch'),
			]
		})

	make_property_setter('Putaway Rule', 'warehouse', 'fetch_from', 'shelf.warehouse', 'Small Text')
