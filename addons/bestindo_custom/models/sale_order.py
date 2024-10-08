# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
from datetime import datetime
import itertools

SALE_ORDER_STATE = [
	('draft', "Draft"),
	('sent', "Checking"),
	('sale', "Confirmed"),
	('waiting_for_approval', "Waiting For Approval"),
	('cancel', "Cancelled"),
	('done', "Done")
]

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	driver_id = fields.Many2one('res.users','Driver')
	state = fields.Selection(
		selection=SALE_ORDER_STATE,
		string="Status",
		readonly=True, copy=False, index=True,
		tracking=3,
		default='draft')
	transfer_img = fields.Binary('Image')
	address_type = fields.Selection([
		('business','Business'),
		('home','Home'),
		('custom','Custom')
	],string="Address Type", default='business')
	full_address = fields.Char('Address', compute='_compute_full_address')
	custom_address = fields.Char('Custom Address')
	provider_id = fields.Many2one('payment.provider','Payment Provider')
	total_deposit = fields.Monetary('Deposit')
	total_point = fields.Integer('Point')
	total_discount = fields.Float('Discount',compute='_compute_total_discount')
	total_ongkir = fields.Float('Ongkir',compute='_compute_total_ongkir')
	is_cod = fields.Boolean('COD')
	is_pickup = fields.Boolean('Pickup')
	point_ids = fields.One2many('bp.member.point','sale_id','Points')

	#Order Info
	payment_date = fields.Date('Payment Date',compute='_compute_payment_info',store=True)
	payment_state = fields.Selection([
		('not_paid','Not Paid'),
		('in_payment','In Payment'),
		('partial','Partially Paid'),
		('paid','Paid'),
		('reversed','Reversed')
	],string="Payment Status",compute='_compute_payment_info',store=True)
	delivery_date = fields.Datetime('Delivery Date',compute='_compute_delivery_info')
	delivery_done_date = fields.Datetime('Delivery Done Date',compute='_compute_delivery_info')
	order_state = fields.Selection([
		('dibuat','Order dibuat'),
		('dikemas','Sedang diproses'),
		('proses','Dalam Pengiriman'),
		('terkirim','Diterima')
	],string="Order Status",compute='_compute_delivery_info')
	date_packed = fields.Datetime('Date Packed')
	date_received = fields.Datetime('Date Received')
	recipient_name = fields.Char('Recipient Name',compute='_compute_delivery_info')

	bp_term_id = fields.Many2one('bp.term','Term')
	po_number = fields.Char('No. PO')
	log_number = fields.Char('Log Number')

	@api.model
	def create(self, vals):
		"""Method for generating sequence for quotation """
		res = super(SaleOrder, self).create(vals)
		seq_val = self.env.ref(
			'bestindo_custom.bp_seq_sale_order').id
		sequences = self.env['ir.sequence'].browse(
			seq_val).next_by_id()
		res.name = sequences
		res.quotation_ref = sequences
		return res

	def _compute_full_address(self):
		for rec in self:
			if rec.partner_id:
				partner = rec.partner_id
				if rec.address_type == 'business':
					rec.full_address = partner.full_address
				elif rec.address_type == 'home':
					rec.full_address = partner.full_address2
				else:
					rec.full_address = False
			else:
				rec.full_address = False

	@api.depends('invoice_ids.state', 'invoice_ids.payment_state', 'invoice_ids.move_type')
	def _compute_payment_info(self):
		for rec in self:
			invoice_id = rec.invoice_ids.filtered(lambda p: p.state == 'posted' and p.move_type == 'out_invoice')
			if invoice_id:
				invoice_id = invoice_id[0]
				payment_id = self.env['account.payment'].search([('ref','=',invoice_id.name)], limit=1, order='id desc')
				rec.payment_state = invoice_id.payment_state
				if payment_id:
					rec.payment_date = payment_id.date
				else:
					rec.payment_date = False
			else:
				rec.payment_state = False
				rec.payment_date = False

	def _compute_delivery_info(self):
		for rec in self:
			picking_id = rec.picking_ids.filtered(lambda p: p.state != 'cancel')
			if picking_id:
				picking_id = picking_id[0]
				order_state = False
				if picking_id.delivery_status in ['ready']:
					order_state = 'dikemas'
				if picking_id.delivery_status in ['on_process','on_hold']:
					order_state = 'proses'
				if picking_id.delivery_status in ['done']:
					order_state = 'terkirim'
				rec.order_state = order_state
				rec.delivery_date = picking_id.scheduled_date
				rec.delivery_done_date = picking_id.date_done
				rec.recipient_name = picking_id.recipient_name if picking_id.recipient_name else rec.partner_id.name
			else:
				rec.order_state = 'dibuat'
				rec.delivery_date = False
				rec.delivery_done_date = False
				rec.recipient_name = False

	@api.depends('order_line')
	def _compute_total_discount(self):
		discount_product_id = self.env.company.discount_product_id
		for rec in self:
			final_promotion_price = 0
			for line in rec.order_line:
				promotion_price = 0
				if line.product_id.detailed_type == 'service':
					continue
				if line.product_id:
					promotion_line_id = self.env['bp.promotion.line'].search([('product_id','=',line.product_id.id),('promotion_id','!=',False),('promotion_id.state','=','open')], limit=1, order='id desc')
					if promotion_line_id:
						promotion_id = promotion_line_id.promotion_id
						if promotion_id.start_date and promotion_id.end_date:
							if (datetime.now() > promotion_id.start_date and datetime.now() < promotion_id.end_date) and promotion_id.state == 'open':
								if promotion_id.disc_type == 'flat':
									promotion_price = line.product_uom_qty*promotion_id.disc_flat
									line.disc_flat = promotion_id.disc_flat
								if promotion_id.disc_type == 'percent':
									promotion_price = line.product_uom_qty*(line.product_id.lst_price*promotion_id.disc_percent)
									line.disc_percent = promotion_id.disc_percent
						else:
							if promotion_id.disc_type == 'flat':
								promotion_price = line.product_uom_qty*promotion_id.disc_flat
								line.disc_flat = promotion_id.disc_flat
							if promotion_id.disc_type == 'percent':
								promotion_price = line.product_uom_qty*(line.product_id.lst_price*promotion_id.disc_percent)
								line.disc_percent = promotion_id.disc_percent

					promotion_all_prod_id = self.env['bp.promotion'].search([('is_all_product','=',True),('state','=','open')], limit=1, order='id desc')
					if promotion_all_prod_id:
						if promotion_all_prod_id.start_date and promotion_all_prod_id.end_date:
							if (datetime.now() > promotion_all_prod_id.start_date and datetime.now() < promotion_all_prod_id.end_date):
								if promotion_all_prod_id.disc_type == 'flat':
									promotion_price = line.product_uom_qty*promotion_all_prod_id.disc_flat
									line.disc_flat = promotion_all_prod_id.disc_flat
								if promotion_all_prod_id.disc_type == 'percent':
									promotion_price = line.product_uom_qty*(line.product_id.lst_price*promotion_all_prod_id.disc_percent)
									line.disc_percent = promotion_all_prod_id.disc_percent
						else:
							if promotion_all_prod_id.disc_type == 'flat':
								promotion_price = line.product_uom_qty*promotion_all_prod_id.disc_flat
								line.disc_flat = promotion_all_prod_id.disc_flat
							if promotion_all_prod_id.disc_type == 'percent':
								promotion_price = line.product_uom_qty*(line.product_id.lst_price*promotion_all_prod_id.disc_percent)
								line.disc_percent = promotion_all_prod_id.disc_percent
				final_promotion_price += promotion_price
			order_id = rec._origin.id or rec.id
			if discount_product_id and final_promotion_price:
				discount_line_id = self.env['sale.order.line'].search([('order_id','=',order_id or rec.id),('product_id','=',discount_product_id.id)], limit=1, order='id desc')
				if discount_line_id:
					discount_line_id.write({'price_unit': final_promotion_price*-1})
				else:
					if type(order_id) == int:
						discount_line_id = self.env['sale.order.line'].create({
							'order_id': order_id or rec.id,
							'product_uom_qty': 1,
							'price_unit': final_promotion_price*-1,
							'product_id': discount_product_id.id,
							'name': discount_product_id.name,
							'sequence': 999

						})
				rec.total_discount = final_promotion_price
			else:
				rec.total_discount = 0
		
	@api.depends('amount_total','carrier_id')
	def _compute_total_ongkir(self):
		ongkir_product_id = self.env.company.ongkir_product_id
		for rec in self:
			order_id = rec._origin.id or rec.id
			ongkir_line_id = self.env['sale.order.line'].search([('order_id','=',order_id or rec.id),('product_id','=',ongkir_product_id.id)], limit=1, order='id desc')
			if rec.carrier_id:
				amount_total = sum(rec.order_line.filtered(lambda p: p.product_id.detailed_type != 'service').mapped('price_subtotal'))
				ongkir = rec.carrier_id.total_ongkir(amount_total)
				
				if ongkir_line_id:
					ongkir_line_id.write({'price_unit': ongkir})
				else:
					if type(order_id) == int:
						ongkir_line_id = self.env['sale.order.line'].create({
							'order_id': order_id or rec.id,
							'product_uom_qty': 1,
							'price_unit': ongkir,
							'product_id': ongkir_product_id.id,
							'name': ongkir_product_id.name,
							'sequence': 1000
						})
				rec.total_ongkir = ongkir
			else:
				if ongkir_line_id:
					self.env.cr.execute("""
						SELECT id FROM sale_order_line 
						WHERE id = %s
					""", (ongkir_line_id.id,))
					result = self.env.cr.fetchone()
					del_ongkir_line_id = result[0] if result else None
					if del_ongkir_line_id:
						self.env.cr.execute("""
							DELETE FROM sale_order_line WHERE id = %s
						""", (del_ongkir_line_id,))
				rec.total_ongkir = 0

	# Dashboard function
	@api.model
	def get_data(self):

		"""To get data to the sales dashboard."""
		domain = []
		quotation = self.env['sale.order'].search(
			domain + [('state', '=', 'draft')])
		my_sale_order_templates = self.env['sale.order'].search(
			domain + [('state', '!=', 'cancel')])
		quotation_sent = self.env['sale.order'].search(
			domain + [('state', '=', 'sent')])
		quotation_cancel = self.env['sale.order'].search(
			domain + [('state', '=', 'cancel')])
		customers = self.env['res.partner'].search([('user_type', '=', 'customer'),('is_another_address','=',False),('id','not in',[1,3])])
		to_invoice = self.env['sale.order'].search(
			domain + [('invoice_status', '=', 'to invoice')])
		products = self.env['product.template'].search([('detailed_type','!=','service')])
		
		return {
			'quotation': len(quotation),
			'my_sale_order_templates': len(my_sale_order_templates),
			'quotation_sent': len(quotation_sent),
			'quotation_cancel': len(quotation_cancel),
			'customers': len(customers),
			'products': len(products),
			'to_invoice': len(to_invoice),
		}

	@api.model
	def get_value(self, start_date, end_date):
		
		"""It is to pass values according to start and end date to the
		dashboard."""
		domain = []
		if start_date and end_date:
			domain = [('date_order', '>=', start_date),
					  ('date_order', '<=', end_date)]
		elif start_date:
			domain = [('date_order', '>=', start_date)]
		elif end_date:
			domain = [('date_order', '<=', end_date)]

		quotation = self.env['sale.order'].search(
			domain + [('state', '=', 'draft')])
		my_sale_order_templates = self.env['sale.order'].search(
			domain + [('state', '!=', 'cancel')])
		quotation_sent = self.env['sale.order'].search(
			domain + [('state', '=', 'sent')])
		quotation_cancel = self.env['sale.order'].search(
			domain + [('state', '=', 'cancel')])
		customers = self.env['res.partner'].search([('user_type', '=', 'customer'),('is_another_address','=',False),('id','not in',[1,3])])
		products = self.env['product.template'].search([('detailed_type','!=','service')])
		to_invoice = self.env['sale.order'].search(
			domain + [('invoice_status', '=', 'to invoice')])

		return {
			'quotation': len(quotation),
			'my_sale_order_templates': len(my_sale_order_templates),
			'quotation_sent': len(quotation_sent),
			'quotation_cancel': len(quotation_cancel),
			'customers': len(customers),
			'products': len(products),
			'to_invoice': len(to_invoice),
		}

	@api.model
	def get_lead_customer(self, start_date=False, end_date=False):
		"""Returns customer data to the graph of dashboard"""
		lead_template = {}
		sale = {}
		domain = [('state','in',['sale','done'])]
		if start_date and end_date:
			domain += [('date_order', '>=', start_date),
					  ('date_order', '<=', end_date)]
		elif start_date:
			domain += [('date_order', '>=', start_date)]
		elif end_date:
			domain += [('date_order', '<=', end_date)]
		
		partner_id = self.env['res.partner'].sudo().search([('user_type','=','customer'),('is_another_address','=',False)])
		sale_ids = self.env['sale.order'].sudo().search(domain)
		vals = sale_ids.mapped('partner_id').ids
		for record in partner_id:
			if record.id in vals:
				total_sale = len(sale_ids.filtered(lambda p: p.partner_id.id == record.id))
				sale.update({record: total_sale})
		sort = dict(
			sorted(sale.items(), key=lambda item: item[1], reverse=True))
		out = dict(itertools.islice(sort.items(), 10))
		for count in out:
			lead_template[count.name] = out[count]
		return {
			'lead_templates': lead_template,
		}

	@api.model
	def get_lead_product(self, start_date=False, end_date=False):
		"""Returns product data to the graph of dashboard"""
		lead_template = {}
		sale = {}
		domain = [('order_id.state','in',['sale','done'])]
		if start_date and end_date:
			domain += [('order_id.date_order', '>=', start_date),
					  ('order_id.date_order', '<=', end_date)]
		elif start_date:
			domain += [('order_id.date_order', '>=', start_date)]
		elif end_date:
			domain += [('order_id.date_order', '<=', end_date)]
		# product_id = self.env['product.template'].search([('detailed_type','!=','service')])
		product_id = self.env['product.product'].search([('detailed_type','!=','service')])
		sale_line_ids = self.env['sale.order.line'].sudo().search(domain)
		vals = sale_line_ids.mapped('product_id').ids
		for record in product_id:
			if record.id in vals:
				sales_count = sum(sale_line_ids.filtered(lambda p: p.product_id.id == record.id).mapped('product_uom_qty'))
				sale.update({record: sales_count})
		sort = dict(
			sorted(sale.items(), key=lambda item: item[1], reverse=True))
		out = dict(itertools.islice(sort.items(), 10))
		for product in out:
			full_name = product.name
			if product.product_template_variant_value_ids:
				variant_name = ' - '.join(x.name for x in product.product_template_variant_value_ids)
				full_name = f"{product.name} ({variant_name})"
			lead_template[full_name] = out[product]
		return {
			'lead_templates': lead_template,
		}
	
	@api.model
	def get_least_sold(self, start_date=False, end_date=False):
		"""Returns least sold product data to the graph of dashboard"""
		lead_template = {}
		sale = {}
		domain = [('order_id.state','in',['sale','done'])]
		if start_date and end_date:
			domain += [('order_id.date_order', '>=', start_date),
					  ('order_id.date_order', '<=', end_date)]
		elif start_date:
			domain += [('order_id.date_order', '>=', start_date)]
		elif end_date:
			domain += [('order_id.date_order', '<=', end_date)]
		# product_id = self.env['product.template'].search([('detailed_type','!=','service')])
		product_id = self.env['product.product'].search([('detailed_type','!=','service')])
		sale_line_ids = self.env['sale.order.line'].sudo().search(domain)
		vals = sale_line_ids.mapped('product_id').ids
		for record in product_id:
			if record.id in vals:
				sales_count = sum(sale_line_ids.filtered(lambda p: p.product_id.id == record.id).mapped('product_uom_qty'))
				sale.update({record: sales_count})
		sort = dict(
			sorted(sale.items(), key=lambda item: item[1], reverse=False))
		out = dict(itertools.islice(sort.items(), 10))
		for product in out:
			full_name = product.name
			if product.product_template_variant_value_ids:
				variant_name = ' - '.join(x.name for x in product.product_template_variant_value_ids)
				full_name = f"{product.name} ({variant_name})"
			lead_template[full_name] = out[product]
		return {
			'lead_templates': lead_template,
		}

	@api.model
	def get_lead_order(self, start_date=False, end_date=False):
		"""Returns lead sale order data to the graph of dashboard"""
		lead_template = {}
		sale = {}
		domain = [('state','in',['sale','done'])]
		if start_date and end_date:
			domain += [('date_order', '>=', start_date),
					  ('date_order', '<=', end_date)]
		elif start_date:
			domain += [('date_order', '>=', start_date)]
		elif end_date:
			domain += [('date_order', '<=', end_date)]
		order_id = self.env['sale.order'].search(domain)
		for record in order_id:
			sale.update({record: record.amount_total})
		sort = dict(
			sorted(sale.items(), key=lambda item: item[1], reverse=True))
		out = dict(itertools.islice(sort.items(), 10))
		for order in out:
			lead_template[order.name] = out[order]
		return {
			'lead_templates': lead_template,
		}

	@api.model
	def get_my_monthly_comparison(self, start_date=False, end_date=False):
		"""Returns my monthly sale count data to the graph of dashboard"""
		lead_template = {}
		# domain = [('state','in',['sale','done'])]
		domain = []
		if start_date and end_date:
			domain += [('date_order', '>=', start_date),
					  ('date_order', '<=', end_date)]
		elif start_date:
			domain += [('date_order', '>=', start_date)]
		elif end_date:
			domain += [('date_order', '<=', end_date)]
		sales_order = self.env['sale.order'].search(domain)
		
		list = [rec.date_order.month for rec in sales_order]
		for i in range(1, 13):
			count = list.count(i)
			lead_template.update({
				i: count
			})
		return {
			'lead_templates': lead_template,
		}
	#End of Dashboard function

	def action_check(self):
		for order in self:
			if not order.order_line:
				raise UserError(_('Order Lines is Empty!'))
			order.write({'state':'sent'})
		return True

	def _bp_create_invoice(self):
		if self.invoice_ids:
			invoice_ids = self.invoice_ids.filtered(lambda p: p.state == 'cancel' and p.move_type == 'out_invoice')
			if invoice_ids:
				invoice_id = self._create_invoices()
		else:
			invoice_id = self._create_invoices()

		return invoice_id

	def action_confirm(self):
		""" Confirm the given quotation(s) and set their confirmation date.

		If the corresponding setting is enabled, also locks the Sale Order.

		:return: True
		:rtype: bool
		:raise: UserError if trying to confirm cancelled SO's
		"""
		
		if not all(order._can_be_confirmed() for order in self):
			raise UserError(_(
				"The following orders are not in a state requiring confirmation: %s",
				", ".join(self.mapped('display_name')),
			))

		self.order_line._validate_analytic_distribution()

		for order in self:
			# if not order.transfer_img and order.provider_id.name not in ['Credit','Deposit','Cash','COD']:
			# 	raise ValidationError(_('Please upload Transfer Image!'))
			if not order.order_line:
				raise UserError(_('Order Lines is Empty!'))
			
			for line in order.order_line:
				if line.product_id.point_type == 'flat':
					if line.product_id.flat_point:
						self.env['bp.member.point'].create({
							'name': order.name,
							'sale_id': order.id,
							'product_id': line.product_id.id,
							'date': order.date_order,
							'point': line.product_id.flat_point*line.product_uom_qty,
							'partner_id':order.partner_id.id
						})
				if line.product_id.point_type == 'percent':
					if line.product_id.percent_point:
						self.env['bp.member.point'].create({
							'name': order.name,
							'sale_id': order.id,
							'product_id': line.product_id.id,
							'date': order.date_order,
							'point': (line.product_id.percent_point*line.product_id.lst_price)*line.product_uom_qty,
							'partner_id':order.partner_id.id
						})

				if not line.product_id.point_type:
					product_tmpl_id = line.product_id.product_tmpl_id
					if product_tmpl_id.point_type == 'flat':
						if product_tmpl_id.flat_point:
							self.env['bp.member.point'].create({
								'name': order.name,
								'sale_id': order.id,
								'product_tmpl_id': product_tmpl_id.id,
								'date': order.date_order,
								'point': product_tmpl_id.flat_point*line.product_uom_qty,
								'partner_id':order.partner_id.id
							})
					if product_tmpl_id.point_type == 'percent':
						if product_tmpl_id.percent_point:
							self.env['bp.member.point'].create({
								'name': order.name,
								'sale_id': order.id,
								'product_tmpl_id': product_tmpl_id.id,
								'date': order.date_order,
								'point': (product_tmpl_id.percent_point*product_tmpl_id.list_price)*line.product_uom_qty,
								'partner_id':order.partner_id.id
							})


			if order.total_point:
				order.action_add_point(point=order.total_point)
				self.env['bp.member.point'].create({
					'name': order.name,
					'sale_id': order.id,
					'date': order.date_order,
					'point': order.total_point*-1,
					'partner_id':order.partner_id.id
				})
					
			if order.provider_id.is_deposit:
				if order.total_deposit > 0:
					self.env['bp.deposit'].create({
						'name': order.name,
						'partner_id': order.partner_id.id,
						'total': order.total_deposit*-1,
						'date': order.date_order,
						'user_id': self.env.user.id,
						'state': 'used',
						'sale_id': order.id
					})
			order.date_packed = datetime.now()

			order.validate_taxes_on_sales_order()
			if order.partner_id in order.message_partner_ids:
				continue
			order.message_subscribe([order.partner_id.id])

		self.write(self._prepare_confirmation_values())

		# Context key 'default_name' is sometimes propagated up to here.
		# We don't need it and it creates issues in the creation of linked records.
		context = self._context.copy()
		context.pop('default_name', None)

		self.with_context(context)._action_confirm()
		invoice = self._bp_create_invoice()
		if invoice.state != 'posted':
			invoice.action_post()
		
		# if self.picking_ids and (self.provider_id.is_credit or self.provider_id.is_cod): #Open if Transfer Image required
		if self.picking_ids:
			self.picking_ids.write({'delivery_status':'ready'})

		if self.provider_id.is_credit:
			invoice.is_credit = True


		# if self.provider_id.is_deposit or self.provider_id.is_bank: #Open if Transfer Image required
		if self.provider_id.is_deposit or self.provider_id.is_cash:	
			context = dict(self.env.context)
			context.update({'active_id': invoice.id,'active_model':'account.move','active_ids': [invoice.id]})
			reg_id = invoice.action_register_payment()
			fields_list=['payment_date','writeoff_label','line_ids','register_line_ids']
			def_reg_id = self.env['account.payment.register'].with_context(context).default_get(fields_list)
			register_id = self.env['account.payment.register'].with_context(context).create(def_reg_id)
			register_id.action_create_payments()
		self.filtered(lambda so: so._should_be_locked()).action_lock()

		return True

	def action_to_done(self):
		for order in self:
			order.write({'state':'done','invoice_status':'invoiced'})

	def action_cancel(self):
		""" Cancel SO after showing the cancel wizard when needed. (cfr :meth:`_show_cancel_wizard`)

		For post-cancel operations, please only override :meth:`_action_cancel`.

		note: self.ensure_one() if the wizard is shown.
		"""
		if any(order.locked for order in self):
			raise UserError(_("You cannot cancel a locked order. Please unlock it first."))
		cancel_warning = self._show_cancel_wizard()
		if cancel_warning:
			self.ensure_one()
			template_id = self.env['ir.model.data']._xmlid_to_res_id(
				'sale.mail_template_sale_cancellation', raise_if_not_found=False
			)
			lang = self.env.context.get('lang')
			template = self.env['mail.template'].browse(template_id)
			if template.lang:
				lang = template._render_lang(self.ids)[self.id]
			ctx = {
				'default_template_id': template_id,
				'default_order_id': self.id,
				'mark_so_as_canceled': True,
				'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
				'model_description': self.with_context(lang=lang).type_name,
			}
			return {
				'name': _('Cancel %s', self.type_name),
				'view_mode': 'form',
				'res_model': 'sale.order.cancel',
				'view_id': self.env.ref('sale.sale_order_cancel_view_form').id,
				'type': 'ir.actions.act_window',
				'context': ctx,
				'target': 'new'
			}
		else:
			deposit_id = self.env['bp.deposit'].search([('sale_id','=',self.id),('state','=','used')], limit=1, order='id desc')
			if deposit_id:
				deposit_id.state = 'cancel'

			# point_product_id = self.env.company.point_product_id
			# if not point_product_id:
			# 	raise ValidationError(_('Mohon isi Service Product untuk Point\n.Settings >> Companies >> Service Product'))

			# search_point = self.env['sale.order.line'].search([('order_id','=',self.id),('product_id','=',point_product_id.id)])
			point_id = self.env['bp.member.point'].search([('sale_id','=',self.id)])
			if point_id:
				point_id.unlink()

			if self.invoice_ids:
				for inv in self.invoice_ids:
					if inv.payment_state != 'not_paid':
						raise UserError(_("Invoice sudah ada transaksi pembayaran.\nMohon cancel pembayaran atau return Invoice."))
					if inv.state != 'cancel':
						inv.button_cancel()
			return self._action_cancel()

	@api.depends('state', 'order_line.invoice_status')
	def _compute_invoice_status(self):
		"""
		Compute the invoice status of a SO. Possible statuses:
		- no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
		  invoice. This is also the default value if the conditions of no other status is met.
		- to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
		- invoiced: if all SO lines are invoiced, the SO is invoiced.
		- upselling: if all SO lines are invoiced or upselling, the status is upselling.
		"""
		confirmed_orders = self.filtered(lambda so: so.state in ['sale','done'])
		(self - confirmed_orders).invoice_status = 'no'
		if not confirmed_orders:
			return
		lines_domain = [('is_downpayment', '=', False), ('display_type', '=', False)]
		line_invoice_status_all = [
			(order.id, invoice_status)
			for order, invoice_status in self.env['sale.order.line']._read_group(
				lines_domain + [('order_id', 'in', confirmed_orders.ids)],
				['order_id', 'invoice_status']
			)
		]
		for order in confirmed_orders:
			line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]
			if order.state not in ['sale','done']:
				order.invoice_status = 'no'
			elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
				if any(invoice_status == 'no' for invoice_status in line_invoice_status):
					# If only discount/delivery/promotion lines can be invoiced, the SO should not
					# be invoiceable.
					invoiceable_domain = lines_domain + [('invoice_status', '=', 'to invoice')]
					invoiceable_lines = order.order_line.filtered_domain(invoiceable_domain)
					special_lines = invoiceable_lines.filtered(
						lambda sol: not sol._can_be_invoiced_alone()
					)
					if invoiceable_lines == special_lines:
						order.invoice_status = 'no'
					else:
						order.invoice_status = 'to invoice'
				else:
					order.invoice_status = 'to invoice'
			elif line_invoice_status and all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
				order.invoice_status = 'invoiced'
			elif line_invoice_status and all(invoice_status in ('invoiced', 'upselling') for invoice_status in line_invoice_status):
				order.invoice_status = 'upselling'
			else:
				order.invoice_status = 'no'

	def action_add_deposit(self):
		product_id = self.env.company.deposit_product_id
		if not product_id:
			raise ValidationError(_('Mohon isi Service Product untuk Deposit\n.Settings >> Companies >> Service Product'))
		for rec in self:
			order_line_id = self.env['sale.order.line'].create({
				'product_id': product_id.id,
				'product_uom_qty': 1,
				'order_id':rec.id
			})

		return True

	def action_add_point(self, point=0):
		product_id = self.env.company.point_product_id
		if not product_id:
			raise ValidationError(_('Mohon isi Service Product untuk Point\n.Settings >> Companies >> Service Product'))
		for rec in self:
			order_line_id = self.env['sale.order.line'].search([('order_id','=',rec.id),('product_id','=',product_id.id)])
			if not order_line_id:
				order_line_id = self.env['sale.order.line'].create({
					'product_id': product_id.id,
					'product_uom_qty': 1,
					'order_id':rec.id,
					'price_unit': point*-1,
					'is_downpayment': False
				})

		return True

	@api.onchange('provider_id')
	def _onchange_provider_id(self):
		if self.provider_id:
			if self.provider_id.is_cod:
				self.is_cod = True
			else:
				self.is_cod = False

	@api.onchange('carrier_id')
	def _onchange_carrier_id_pickup(self):
		if self.carrier_id:
			if self.carrier_id.is_cod:
				self.is_pickup = True
			else:
				self.is_pickup = False

class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	disc_flat = fields.Float('Discount Flat')
	disc_percent = fields.Float('Discount Percent')

	# @api.depends('product_id', 'product_uom', 'product_uom_qty')
	# def _compute_price_unit(self):
	# 	for line in self:
	# 		# check if there is already invoiced amount. if so, the price shouldn't change as it might have been
	# 		# manually edited
	# 		if line.qty_invoiced > 0 or (line.product_id.expense_policy == 'cost' and line.is_expense):
	# 			continue
	# 		if not line.product_uom or not line.product_id:
	# 			line.price_unit = 0.0
	# 		else:
	# 			line = line.with_company(line.company_id)
	# 			price = line._get_display_price()
	# 			line.price_unit = line.product_id._get_tax_included_unit_price_from_price(
	# 				price,
	# 				line.currency_id or line.order_id.currency_id,
	# 				product_taxes=line.product_id.taxes_id.filtered(
	# 					lambda tax: tax.company_id == line.env.company
	# 				),
	# 				fiscal_position=line.order_id.fiscal_position_id,
	# 			)

	@api.model
	def create(self, vals):
		context = self.env.context
		product_id= vals.get('product_id')
		uom_id = vals.get('product_uom')
		if product_id:
			product_variant = self.env['product.product'].browse(product_id)
			product_uom = self.env['uom.uom'].browse(uom_id)
			if product_variant.detailed_type != 'service':
				if vals.get('price_unit'):
					if vals.get('price_unit') < 0:
						raise ValidationError("Error: The price unit cannot be negative for this products.")
				if vals.get('product_uom_qty'):
					if vals.get('product_uom_qty') < product_uom.rounding:
						raise UserError(f"{vals.get('name')}\nCan't set Quantity less than [{product_uom.rounding}] Rounding Precision on Unit: {product_uom.name}")

		result = super(SaleOrderLine, self.with_context(context)).create(vals)
		return result

	@api.model
	def write(self, vals):
		context = self.env.context
		if self.product_id:
			if self.product_id.detailed_type != 'service':
				if vals.get('price_unit') :
					if vals.get('price_unit') < 0:
						raise ValidationError("Error: The price unit cannot be negative for this products.")
				if vals.get('product_uom_qty'):
					if vals.get('product_uom_qty') < self.product_uom.rounding:
						raise ValidationError(f"{self.name}\nCan't set Quantity less than [{self.product_uom.rounding}] Rounding Precision on Unit: {self.product_uom.name}")
			else:
				if vals.get('product_uom_qty'):
					if vals.get('product_uom_qty') != 1:
						raise ValidationError(f"Error: The cannot update qty for {self.product_id.name}.")

		result = super(SaleOrderLine, self.with_context(context)).write(vals)
		return result