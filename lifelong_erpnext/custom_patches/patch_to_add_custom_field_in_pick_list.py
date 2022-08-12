import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field, create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def execute():
	frappe.reload_doc('stock', 'doctype', 'pick_list')

	df = dict(fieldname='child_warehouse', insert_after='parent_warehouse',
		label='Child Warehouse', fieldtype='Link', options='Warehouse', depends_on='parent_warehouse')

	create_custom_field("Pick List", df)

	df = dict(fieldname='select_manually', insert_after='child_warehouse',
		label='Select Shelf Manually', fieldtype='Check')

	create_custom_field("Pick List", df)