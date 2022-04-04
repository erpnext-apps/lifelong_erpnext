import frappe
from frappe.utils import nowdate, flt
from lifelong_erpnext.lifelong_erpnext.report.shelf_wise_batch_balance_report.shelf_wise_batch_balance_report import execute

def get_stock_balance(args, operator=None,
	order="desc", limit=None, for_update=False, debug=False, check_serial_no=True):
	"""get stock ledger entries filtered by specific posting datetime conditions"""
	conditions = " and timestamp(posting_date, posting_time) {0} timestamp(%(posting_date)s, %(posting_time)s)".format(operator)
	if args.get("warehouse"):
		conditions += " and warehouse = %(warehouse)s"

	if args.get("shelf"):
		conditions += " and shelf = %(shelf)s"

	if check_serial_no and args.get("serial_no"):
		# conditions += " and serial_no like {}".format(frappe.db.escape('%{0}%'.format(args.get("serial_no"))))
		serial_no = args.get("serial_no")
		conditions += (""" and
			(
				serial_no = {0}
				or serial_no like {1}
				or serial_no like {2}
				or serial_no like {3}
			)
		""").format(frappe.db.escape(serial_no), frappe.db.escape('{}\n%'.format(serial_no)),
			frappe.db.escape('%\n{}'.format(serial_no)), frappe.db.escape('%\n{}\n%'.format(serial_no)))

	if not args.get("posting_date"):
		args["posting_date"] = "1900-01-01"
	if not args.get("posting_time"):
		args["posting_time"] = "00:00"

	if operator in (">", "<=") and args.get("name"):
		conditions += " and name!=%(name)s"

	entry = frappe.db.sql("""
		select sum(actual_qty) as qty_after_transaction
		from `tabStock Ledger Entry`
		where item_code = %%(item_code)s
		and is_cancelled = 0
		%(conditions)s
		order by timestamp(posting_date, posting_time) %(order)s, creation %(order)s
		%(limit)s %(for_update)s""" % {
			"conditions": conditions,
			"limit": limit or "",
			"for_update": for_update and "for update" or "",
			"order": order
		}, args, as_dict=1)

	return entry[0].qty_after_transaction if entry else 0.0

@frappe.whitelist()
def get_available_batches(item_code, warehouse, company, qty=0, batch_no=None, shelf=None, posting_time=None):
	qty = flt(qty)

	filters = frappe._dict({
		'item_code': item_code,
		'warehouse': warehouse,
		'company': company,
		'from_date': nowdate(),
		'to_date': nowdate(),
		'batch_no': batch_no,
		'shelf': shelf
	})

	if posting_time:
		filters.posting_time = posting_time

	columns, data = execute(filters)

	if not qty:
		return data

	new_data = []
	for row in data:
		if qty <= 0:
			break

		if row.bal_qty > qty:
			row.selected_qty = qty
			new_data.append(row)
			break
		else:
			qty -= row.bal_qty
			row.selected_qty = row.bal_qty
			new_data.append(row)

	return new_data

def create_batch(doc, method):
	non_duplicate_items = {}
	for row in doc.items:
		if row.batch_no:
			continue

		if row.item_code in non_duplicate_items:
			row.batch_no = non_duplicate_items.get(row.item_code)
			continue

		if (doc.doctype == 'Stock Entry' and doc.purpose in ['Repack', 'Manufacture', 'Material Receipt']
			and row.t_warehouse) or doc.doctype == 'Purchase Receipt':
			if not frappe.get_cached_value('Item', row.item_code, 'has_batch_no'):
				continue

			row.batch_no = frappe.get_doc({
				'doctype': 'Batch',
				'item': row.item_code,
				'reference_doctype': doc.doctype,
				'reference_name': doc.name
			}).insert(ignore_permissions=True).name

			non_duplicate_items.setdefault(row.item_code, row.batch_no)

@frappe.whitelist()
def has_batch_no(item_code):
	return frappe.db.get_value('Item', item_code, ['has_batch_no', 'has_serial_no'], as_dict=1)


def update_shelf_for_from_warehouse(doc, method):
	if not doc.is_internal_supplier:
		return

	dn_items = [row.delivery_note_item for row in doc.items if row.delivery_note_item]

	if not dn_items:
		return

	shelf_data = get_shelf_from_delivery_note(dn_items)

	for row in doc.items:
		if row.delivery_note_item in shelf_data:
			row.from_shelf = shelf_data[row.delivery_note_item]

def get_shelf_from_delivery_note(dn_items):
	shelf_dict = frappe._dict({})
	for row in frappe.get_all('Delivery Note Item', fields = ['name', 'target_shelf'],
		filters = {'name': ('in', dn_items)}):
		shelf_dict[row.name] = row.target_shelf

	return shelf_dict
