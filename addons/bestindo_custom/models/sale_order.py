# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

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

	# Dashboard function
	@api.model
	def get_data(self):

		"""To get data to the sales dashboard."""
		domain = [('user_id', '=', self.env.user.id)]
		quotation = self.env['sale.order'].search(
			domain + [('state', '=', 'draft')])
		my_sale_order_templates = self.env['sale.order'].search(
			domain + [('state', '!=', 'cancel')])
		quotation_sent = self.env['sale.order'].search(
			domain + [('state', '=', 'sent')])
		quotation_cancel = self.env['sale.order'].search(
			domain + [('state', '=', 'cancel')])
		customers = self.env['res.partner'].search([('user_type', '=', 'customer'),('is_another_address','=',False)])
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
			domain = [('user_id', '=', self.env.user.id),
					  ('date_order', '>=', start_date),
					  ('date_order', '<=', end_date)]
		elif start_date:
			domain = [('user_id', '=', self.env.user.id),
					  ('date_order', '>=', start_date)]
		elif end_date:
			domain = [('user_id', '=', self.env.user.id),
					  ('date_order', '<=', end_date)]

		quotation = self.env['sale.order'].search(
			domain + [('state', '=', 'draft')])
		my_sale_order_templates = self.env['sale.order'].search(
			domain + [('state', '!=', 'cancel')])
		quotation_sent = self.env['sale.order'].search(
			domain + [('state', '=', 'sent')])
		quotation_cancel = self.env['sale.order'].search(
			domain + [('state', '=', 'cancel')])
		customers = self.env['res.partner'].search([('user_type', '=', 'customer'),('is_another_address','=',False)])
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
	#End of Dashboard function

	def action_check(self):
		for order in self:
			if not order.order_line:
				raise UserError(_('Order Lines is Empty!'))
			order.write({'state':'sent'})
		return True

	def _bp_create_invoice(self):
		if self.invoice_ids:
			for invoice in self.invoice_ids:
				if invoice.state == 'cancel':
					invoice_id = self._create_invoices()
				else:
					invoice_id = invoice
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
			if not order.transfer_img:
				raise ValidationError(_('Please upload Transfer Image!'))
			if not order.order_line:
				raise UserError(_('Order Lines is Empty!'))
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
		if invoice:
			invoice.action_post()
		self.filtered(lambda so: so._should_be_locked()).action_lock()

		return True

	def action_to_done(self):
		for order in self:
			order.write({'state':'done'})