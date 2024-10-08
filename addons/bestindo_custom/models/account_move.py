# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta
import PyPDF2
import io
import base64
import pdfkit

class AccountMove(models.Model):
	_inherit = 'account.move'

	name2 = fields.Char('Inv Number')
	is_payment_done = fields.Boolean('Payment Done')
	return_type = fields.Selection([
		('bank','Bank'),
		('cash','Cash'),
		('wallet','Wallet')
	], string='Return Type', default='bank')
	is_credit = fields.Boolean('Credit Invoice')
	total_point = fields.Integer('Point')

	def write(self, vals):
		if vals.get('name2'):
			vals['payment_reference'] = vals.get('name2')
		return super(AccountMove,self).write(vals)

	def action_post(self):
		moves_with_payments = self.filtered('payment_id')
		other_moves = self - moves_with_payments
		if moves_with_payments:
			moves_with_payments.payment_id.action_post()
		if other_moves:
			other_moves._post(soft=False)

		if not self.name2 or self.name == 'Draft':
			if self.move_type == 'out_refund':
				seq_ref = 'bestindo_custom.bp_seq_account_move_return_invoice'
			else:
				seq_ref = 'bestindo_custom.bp_seq_account_move_invoice'

			seq_val = self.env.ref(seq_ref).id
			sequences = self.env['ir.sequence'].browse(seq_val).next_by_id()
			self.name2 = sequences
			self.payment_reference = sequences
		return False
	
	def button_draft(self):
		for move in self:
			if move.payment_state != 'not_paid':
				raise UserError(_("Can't set to draft, Invoice already partial or paid."))
		if any(move.state not in ('cancel', 'posted') for move in self):
			raise UserError(_("Only posted/cancelled journal entries can be reset to draft."))

		exchange_move_ids = set()
		if self:
			self.env['account.full.reconcile'].flush_model(['exchange_move_id'])
			self.env['account.partial.reconcile'].flush_model(['exchange_move_id'])
			self._cr.execute(
				"""
					SELECT DISTINCT sub.exchange_move_id
					FROM (
						SELECT exchange_move_id
						FROM account_full_reconcile
						WHERE exchange_move_id IN %s

						UNION ALL

						SELECT exchange_move_id
						FROM account_partial_reconcile
						WHERE exchange_move_id IN %s
					) AS sub
				""",
				[tuple(self.ids), tuple(self.ids)],
			)
			exchange_move_ids = set([row[0] for row in self._cr.fetchall()])

		for move in self:
			if move.id in exchange_move_ids:
				raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
			if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
				# If the reconciliation was undone, move.tax_cash_basis_rec_id will be empty;
				# but we still don't want to allow setting the caba entry to draft
				# (it'll have been reversed automatically, so no manual intervention is required),
				# so we also check tax_cash_basis_origin_move_id, which stays unchanged
				# (we need both, as tax_cash_basis_origin_move_id did not exist in older versions).
				raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
			if move.restrict_mode_hash_table and move.state == 'posted':
				raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
			# We remove all the analytics entries for this journal
			move.mapped('line_ids.analytic_line_ids').unlink()

		self.mapped('line_ids').remove_move_reconcile()
		self.write({'state': 'draft', 'is_move_sent': False})

	def get_inv_line(self):
		values = {}
		for move in self:
			sale = self.env['sale.order'].search([('name','=', move.invoice_origin)], limit=1, order='id desc')
			if not sale:
				continue
			line = []
			amount_total = sum(sale.order_line.filtered(lambda p: p.product_id.detailed_type != 'service').mapped('price_subtotal'))
			grand_total = amount_total + sale.total_ongkir - sale.total_discount - sale.total_point

			for x in move.invoice_line_ids:
				if x.product_id.detailed_type == 'service':
					continue
				variant_name = ''
				if x.product_id.product_template_variant_value_ids:
					variant_name = ' - '.join(x.name for x in x.product_id.product_template_variant_value_ids)
				line.append({
					'name': f"{x.product_id.name} ({variant_name})",
					'qty': int(x.quantity),
					'uom': x.product_uom_id.name,
					'price': x.price_unit,
					'total': x.price_subtotal,
					'disc_percent': '',
					'disc_flat': ''
				})
			values.update({
				'customer': move.partner_id.name or '',
				'customer_id': move.partner_id.customer_id or '',
				'phone': move.partner_id.phone or '',
				'invoice_no': move.name2,
				'no_po': sale.po_number or '',
				'date': move.invoice_date.strftime('%d-%b-%y'),
				'term': sale.bp_term_id.name or '',
				'currency': move.currency_id.name,
				'no_log': sale.log_number or '',
				'line': line,
				'ongkir': sale.total_ongkir,
				'point': sale.total_point*-1 if sale.total_point > 0 else 0,
				'discount': sale.total_discount*-1 if sale.total_discount > 0 else 0,
				'deposit': sale.total_deposit,
				'amount_total': amount_total,
				'grand_total': grand_total,
				'bank_name': sale.provider_id.name or '',
				'bank_acc_name': sale.provider_id.acc_name or '' if sale.provider_id else '',
				'bank_acc_number': sale.provider_id.acc_number or '' if sale.provider_id else '',
				'print_date': (datetime.now()+timedelta(hours=7)).strftime('%d/%m/%Y %H:%M:%S')
			})
		return values
	
	def invoice_report2pdf(self):
		pdf_results = []
		for move in self:
			pdf_content, _ = self.env['ir.actions.report'].sudo()._render_qweb_pdf('account.report_invoice_with_payments', [move.id])
			pdf_results.append(pdf_content)

		if pdf_results:
			pdf_writer = PyPDF2.PdfFileWriter()
			for pdf_data in pdf_results:
				pdf = PyPDF2.PdfFileReader(io.BytesIO(pdf_data))
				for page_num in range(pdf.getNumPages()):
					page = pdf.getPage(page_num)
					pdf_writer.addPage(page)

			pdf_bytes = io.BytesIO()
			pdf_writer.write(pdf_bytes)
			pdf_bytes.seek(0)

			pdf_binary = pdf_bytes.getvalue()
			pdf_base64 = base64.b64encode(pdf_binary).decode('utf-8')
			file_name = 'INVOICE-'+(datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H_%M_%S')+'.pdf'
			module_rec = self.env['invoice.report.pdf'].create(
				{'name': file_name, 'pdf_file': pdf_base64})
			return {'name': ('PDF File'),
				'res_id': module_rec.id,
				"view_mode": 'form',
				'res_model': 'invoice.report.pdf',
				'type': 'ir.actions.act_window',
				'target': 'new'}

	def invoice_html2pdf(self):
		pdf_results = []
		for move in self:
			values = move.get_inv_line()
			style = """
				<style>
					.table-cust {
						width: 65%;
					}
					.table-inv {
						width: 30%;
						margin-left: 0px;
					}
					.table-cust-in {
						width: 100%;
						padding-bottom: 15px;
					}
					.cust-col-1 {
						width: 13%;
					}
					.cust-col-2 {
						width: 2%;
					}
					.cust-col-3 {
						width: 85%;
					}
					.inv-col-1 {
						width: 35%;
					}
					.inv-col-2 {
						width: 2%;
					}
					.inv-col-3 {
						width: 63%;
					}
					.page {
						page-break-after: always;
					}
					.bestindo-content {
						width: 100%;
					}
					.bestindo-footer {
						width: 100%;
						margin-top: 5px;
					}
				</style>
			"""

			header = f"""
				<div class="bestindo-header">
					<div class="container">
						<div class="row">
							<div class="col-sm-8 table-cust">
								<table class="table-cust-in">
									<tr style="border-right: 1px solid black">
										<td class="cust-col-1">Customer</td>
										<td class="cust-col-2">:</td>
										<td class="cust-col-3"><b>{values.get('customer','')} ({values.get('customer_id','')})</b></td>
									</tr>
									<tr style="border-right: 1px solid black">
										<td></td>
										<td></td>
										<td>--</td>
									</tr>
									<tr style="height: 40px; border-bottom: 1px solid black; border-right: 1px solid black">
										<td></td>
										<td></td>
										<td>Tel:&#160;&#160;&#160;{values.get('phone','')}&#160;&#160;&#160;Fax: </td>
									</tr>
									<tr>
										<td></td>
										<td></td>
										<td style="font-size: 30px; font-weight: bold; text-align: right; font-family: 'Times New Roman'">TOKO</td>
									</tr>
									<tr>
										<td></td>
										<td></td>
										<td style="text-align: right; padding-right: 7px; padding-top: 30px">Page :&#160;&#160;{len(move)}/{len(self)}</td>
									</tr>
								</table>
							</div>
							<div class="col-sm-4 table-inv">
								<table style="width: 100%">
									<tr>
										<td colspan="3" style="font-size: 25px; font-family: 'Times New Roman';"><u><b>INVOICE</b></u></td>
									</tr>
									<tr>
										<td colspan="3" style="font-size: 18px; font-family: 'Times New Roman';"><b>{values.get('invoice_no','')}</b></td>
									</tr>
									<tr>
										<td class="inv-col-1">No. PO</td>
										<td class="inv-col-2">:</td>
										<td class="inv-col-3">&#160;&#160;{values.get('no_po','')}</td>
									</tr>
									<tr>
										<td>Date</td>
										<td>:</td>
										<td>&#160;&#160;{values.get('date','')}</td>
									</tr>
									<tr>
										<td>Salesman</td>
										<td>:</td>
										<td>&#160;&#160;</td>
									</tr>
									<tr>
										<td>Term</td>
										<td>:</td>
										<td>&#160;&#160;{values.get('term','')}</td>
									</tr>
									<tr>
										<td>Currency</td>
										<td>:</td>
										<td>&#160;&#160;{values.get('currency','')}</td>
									</tr>
									<tr>
										<td>Log No</td>
										<td>:</td>
										<td>&#160;&#160;{values.get('no_log','')}</td>
									</tr>
								</table>
							</div>
						</div>
					</div>
					<div>
						<p>Order by&#160;&#160;:&#160;&#160;</p>
						<table style="width: 100%; border-bottom: 1px solid black">
							<tr style="text-align: center">
								<th style="border: 1px solid black; width: 5%">NO.</th>
								<th style="border: 1px solid black; width: 40%">DESCRIPTION</th>
								<th style="border: 1px solid black; width: 10%">QTY</th>
								<th style="border: 1px solid black; width: 10%">PRICE</th>
								<th style="border: 1px solid black; width: 10%">DISC %</th>
								<th style="border: 1px solid black; width: 10%">DISCOUNT</th>
								<th style="border: 1px solid black; width: 15%">NET AMOUNT</th>
							</tr>
						</table>
					</div>
				</div>
			"""

			invoice_line = """"""
			number = 1
			for line in values.get('line',[]):
				invoice_line += f"""
					<tr>
						<td style="width: 5%;text-align: center">{number}</td>
						<td style="width: 40%">{line.get('name','')}</td>
						<td style="width: 10%;text-align: center">{line.get('qty','')}&#160;&#160;&#160;&#160;{line.get('uom','')}</td>
						<td style="width: 10%;text-align: right">{line.get('price','')}</td>
						<td style="width: 10%;text-align: right">{line.get('disc_percent','')}</td>
						<td style="width: 10%;text-align: right">{line.get('disc_flat','')}</td>
						<td style="width: 15%;text-align: right">{line.get('total','')}</td>
					</tr>\n
				"""
				number += 1

			body = f"""
				<div class="bestindo-content">
					<table style="width: 100%; border-bottom: 1px solid black">
						{invoice_line}
						<tr>
							<td></td>
							<td>--</td>
							<td></td>
							<td></td>
							<td></td>
							<td></td>
							<td></td>
						</tr>
					</table>
				</div>
			"""

			if values.get('bank_name',''):
				footer_info = f"""
					Barang telah diterima dengan baik dan cukup. Pembayaran dg Transfer/Giro:<br/>
					{values.get('bank_acc_name','')}, {values.get('bank_name','')}: {values.get('bank_acc_number','')}<br/>
					dan dianggap sah bila telah diterima oleh bank kami.<br/>
				"""
			else:
				footer_info = """
					Barang telah diterima dengan baik dan cukup. Pembayaran dg Transfer/Giro:<br/>
					PT.BESTINDO PERSADA, BCA: 852 066 1515<br/>
					dan dianggap sah bila telah diterima oleh bank kami.<br/>
				"""

			ongkir = """"""
			if values.get('ongkir',0):
				ongkir = f"""
					<tr>
						<td style="text-align: right">Ongkir&#160;&#160;</td>
						<td>:</td>
						<td style="text-align: center">{values.get('currency','')}</td>
						<td style="text-align: right">{values.get('ongkir',0)}</td>
					</tr>\n
				"""

			point = """"""
			if values.get('point',0):
				point = f"""
					<tr>
						<td style="text-align: right">Point&#160;&#160;</td>
						<td>:</td>
						<td style="text-align: center">{values.get('currency','')}</td>
						<td style="text-align: right">{values.get('point',0)}</td>
					</tr>\n
				"""
			footer = f"""
				<div class="bestindo-footer">
					<div>
						<div class="row">
							<div class="col-sm-8" style="width: 60%">
								<p style="line-height: 1.2">
									{footer_info}
								</p>
							</div>
							<div class="col-sm-4" style="width: 40%">
								<table style="width: 100%; font-weight: bold; font-size: 18px">
									<tr>
										<td style="text-align: right">Total&#160;&#160;</td>
										<td>:</td>
										<td style="text-align: center">{values.get('currency','')}</td>
										<td style="text-align: right">{values.get('amount_total','')}</td>
									</tr>
									{ongkir}
									<tr>
										<td style="text-align: right">Disc&#160;&#160;</td>
										<td>:</td>
										<td style="text-align: center">{values.get('currency','')}</td>
										<td style="text-align: right">{values.get('discount','')}</td>
									</tr>
									{point}
									<tr>
										<td style="text-align: right">Grand Total&#160;&#160;</td>
										<td>:</td>
										<td style="text-align: center">{values.get('currency','')}</td>
										<td style="text-align: right">{values.get('grand_total','')}</td>
									</tr>
								</table>
								<p style="border-top: 1px solid black; width: 65%; margin-left: 130px; margin-top: 5px"/>
							</div>
						</div>
					</div>
					<table style="width: 100%; margin-top: 5px">
						<tr style="text-align: center">
							<td style="width: 33%; line-height: 1.1; vertical-align: middle;">Received in Good<br/>conditions by,</td>
							<td style="width: 33%; vertical-align: middle;">Delivered By,</td>
							<td style="width: 34%; vertical-align: middle;">Admin</td>
						</tr>
						<tr style="text-align: center">
							<td style="padding-top: 35px">(_________________________)</td>
							<td style="padding-top: 35px">(_________________________)</td>
							<td style="padding-top: 35px">(_________________________)</td>
						</tr>
						<tr style="text-align: center">
							<td>Name & Date</td>
							<td></td>
							<td>{values.get('print_date','')}</td>
						</tr>
					</table>
				</div>
			"""
			
			html = f"""
				<!DOCTYPE html>
				<html lang="en">
				<head>
					<meta charset="UTF-8">
					<meta name="viewport" content="width=device-width, initial-scale=1.0">
					<title>Invoice Report</title>
					<link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
					{style}
				</head>
				<body>
					<div class="page">
						{header}
						{body}
						{footer}
					</div>
				</body>
				</html>
			"""

			options = {
				'page-height': '140mm',
				'page-width': '216mm',
				'margin-top': '5mm',
				'margin-right': '10mm',
				'margin-bottom': '5mm',
				'margin-left': '10mm',
				'orientation': 'Portrait',
				'dpi': 50,
			}
			pdf_data = pdfkit.from_string(html, False, options=options)
			if self.env.context.get('from_api',False):
				return pdf_data
			pdf_results.append(pdf_data)

		if pdf_results:
			pdf_writer = PyPDF2.PdfFileWriter()
			for pdf_data in pdf_results:
				pdf = PyPDF2.PdfFileReader(io.BytesIO(pdf_data))
				for page_num in range(pdf.getNumPages()):
					page = pdf.getPage(page_num)
					pdf_writer.addPage(page)

			pdf_bytes = io.BytesIO()
			pdf_writer.write(pdf_bytes)
			pdf_bytes.seek(0)

			pdf_binary = pdf_bytes.getvalue()
			pdf_base64 = base64.b64encode(pdf_binary).decode('utf-8')
			file_name = 'INVOICE-'+(datetime.now()+timedelta(hours=7)).strftime('%Y-%m-%d %H_%M_%S')+'.pdf'
			module_rec = self.env['invoice.report.pdf'].create(
				{'name': file_name, 'pdf_file': pdf_base64})
			return {'name': _('PDF File'),
				'res_id': module_rec.id,
				"view_mode": 'form',
				'res_model': 'invoice.report.pdf',
				'type': 'ir.actions.act_window',
				'target': 'new'}

	def create_payment_from_api(self):
		for invoice in self:
			context = dict(self.env.context)
			context.update({'active_id': invoice.id,'active_model':'account.move','active_ids': [invoice.id],'create_payment_from_api': True})
			reg_id = invoice.action_register_payment()
			fields_list=['payment_date','writeoff_label','line_ids','register_line_ids']
			def_reg_id = self.env['account.payment.register'].with_context(context).default_get(fields_list)
			register_id = self.env['account.payment.register'].with_context(context).create(def_reg_id)
			action_id = register_id.action_create_payments()
		return True

class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	def action_register_payment(self):
		''' Open the account.payment.register wizard to pay the selected journal items.
		:return: An action opening the account.payment.register wizard.
		'''
		return {
			'name': _('Make Payment'),
			'res_model': 'account.payment.register',
			'view_mode': 'form',
			'views': [[False, 'form']],
			'context': {
				'active_model': 'account.move.line',
				'active_ids': self.ids,
			},
			'target': 'new',
			'type': 'ir.actions.act_window',
		}

class AccountJournal(models.Model):
	_inherit = 'account.journal'

	@api.onchange('default_account_id')
	def onchange_default_account_id(self):
		if self.default_account_id:
			if self.outbound_payment_method_line_ids:
				self.outbound_payment_method_line_ids.payment_account_id = self.default_account_id.id
			if self.inbound_payment_method_line_ids:
				self.inbound_payment_method_line_ids.payment_account_id = self.default_account_id.id

class AccountPayment(models.Model):
	_inherit = 'account.payment'

	invoice_id = fields.Many2one('account.move','Invoice')