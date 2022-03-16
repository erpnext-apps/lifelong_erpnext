import frappe

def update_shelf_data(doc, method):
	doctype_mapper = {
		'Purchase Receipt': 'Purchase Receipt Item',
		'Stock Entry': 'Stock Entry Detail',
		'Delivery Note': 'Delivery Note Item',
	}

	if doctype_mapper.get(doc.voucher_type) and doc.voucher_detail_no:
		doc.shelf = frappe.db.get_value(doctype_mapper.get(doc.voucher_type), doc.voucher_detail_no, 'shelf')

	if (doc.voucher_type in ['Stock Entry', 'Purchase Receipt'] and doc.warehouse
		and not doc.shelf and frappe.get_cached_value('Warehouse', doc.warehouse, 'has_shelf')):
		frappe.throw(f"The shelf is required for the warehouse {doc.warehouse}")