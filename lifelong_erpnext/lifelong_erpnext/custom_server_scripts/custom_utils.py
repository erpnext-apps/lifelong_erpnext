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
def get_available_batches(item_code, warehouse, company, qty=0, batch_no=None, shelf=None):
	qty = flt(qty)

	if isinstance(warehouse, str):
		warehouse = [warehouse]

	columns, data = execute(frappe._dict({
		'item_code': item_code,
		'warehouse': warehouse,
		'company': company,
		'from_date': nowdate(),
		'to_date': nowdate(),
		'batch_no': batch_no,
		'shelf': shelf
	}))

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