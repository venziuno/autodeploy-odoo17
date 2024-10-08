# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class StockPicking(models.Model):
	_inherit = 'stock.picking'
	_order = 'id desc'

	driver_id = fields.Many2one('res.users','Driver',related='sale_id.driver_id',store=True)
	driver_img = fields.Binary('Image')
	delivery_status = fields.Selection([
		('draft','Draft'),
		('ready','Ready to Ship'),
		('on_process','On Process'),
		('on_hold','On Hold'),
		('done','Done')
	], string='Delivery Status', default='draft')
	recipient_name = fields.Char('Recipient')
	transaction_count = fields.Integer(compute="_compute_transaction_count", string='Sale Order Count')

	@api.model
	def default_get(self, fields):
		result = super(StockPicking, self).default_get(fields)
		location_id = self.env['stock.location'].search([('name','=','Stock')], limit=1, order='id desc')
		if location_id:
			result['location_id'] = location_id.id
		location_dest_id = self.env['stock.location'].search([('name','=','Customers')], limit=1, order='id desc')
		if location_dest_id:
			result['location_dest_id'] = location_dest_id.id
		picking_type_id = self.env['stock.picking.type'].search([('name','=','Delivery Orders'),('code','=','outgoing')], limit=1, order='id desc')
		if picking_type_id:
			result['picking_type_id'] = picking_type_id.id
		
		return result
	
	@api.depends('sale_id')
	def _compute_transaction_count(self):
		for pick in self:
			pick.transaction_count = len(pick.sale_id)

	@api.onchange('driver_id')
	def onchange_driver_id(self):
		for pick in self:
			if pick.driver_id:
				pick.sale_id.driver_id = pick.driver_id.id

	def button_validate(self):
		draft_picking = self.filtered(lambda p: p.state == 'draft')
		draft_picking.action_confirm()
		for move in draft_picking.move_ids:
			if float_is_zero(move.quantity, precision_rounding=move.product_uom.rounding) and\
			   not float_is_zero(move.product_uom_qty, precision_rounding=move.product_uom.rounding):
				move.quantity = move.product_uom_qty

		# Sanity checks.
		if not self.env.context.get('skip_sanity_check', False):
			self._sanity_check()
		self.message_subscribe([self.env.user.partner_id.id])

		# Run the pre-validation wizards. Processing a pre-validation wizard should work on the
		# moves and/or the context and never call `_action_done`.
		if not self.env.context.get('button_validate_picking_ids'):
			self = self.with_context(button_validate_picking_ids=self.ids)
		res = self._pre_action_done_hook()
		if res is not True:
			return res

		# Call `_action_done`.
		pickings_not_to_backorder = self.filtered(lambda p: p.picking_type_id.create_backorder == 'never')
		if self.env.context.get('picking_ids_not_to_backorder'):
			pickings_not_to_backorder |= self.browse(self.env.context['picking_ids_not_to_backorder']).filtered(
				lambda p: p.picking_type_id.create_backorder != 'always'
			)
		pickings_to_backorder = self - pickings_not_to_backorder
		pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()
		pickings_to_backorder.with_context(cancel_backorder=False)._action_done()
		report_actions = self._get_autoprint_report_actions()
		another_action = False

		if self.sale_id:
			invoice_paid = self.sale_id.invoice_ids.filtered(lambda p: p.payment_state == 'paid' and p.move_type == 'out_invoice')
			if invoice_paid:
				self.sale_id.action_to_done()
		self.delivery_status = 'done'

		if self.user_has_groups('stock.group_reception_report'):
			pickings_show_report = self.filtered(lambda p: p.picking_type_id.auto_show_reception_report)
			lines = pickings_show_report.move_ids.filtered(lambda m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity and not m.move_dest_ids)
			if lines:
				# don't show reception report if all already assigned/nothing to assign
				wh_location_ids = self.env['stock.location']._search([('id', 'child_of', pickings_show_report.picking_type_id.warehouse_id.view_location_id.ids), ('usage', '!=', 'supplier')])
				if self.env['stock.move'].search([
						('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
						('product_qty', '>', 0),
						('location_id', 'in', wh_location_ids),
						('move_orig_ids', '=', False),
						('picking_id', 'not in', pickings_show_report.ids),
						('product_id', 'in', lines.product_id.ids)], limit=1):
					action = pickings_show_report.action_view_reception_report()
					action['context'] = {'default_picking_ids': pickings_show_report.ids}
					if not report_actions:
						return action
					another_action = action
		if report_actions:
			return {
				'type': 'ir.actions.client',
				'tag': 'do_multi_print',
				'params': {
					'reports': report_actions,
					'anotherAction': another_action,
				}
			}
		return True

	def action_open_transaction(self):
		self.ensure_one()
		source_orders = self.sale_id
		result = self.env['ir.actions.act_window']._for_xml_id('sale.action_orders')
		if len(source_orders) > 1:
			result['domain'] = [('id', 'in', source_orders.ids)]
		elif len(source_orders) == 1:
			result['views'] = [(self.env.ref('sale.view_order_form', False).id, 'form')]
			result['res_id'] = source_orders.id
		else:
			result = {'type': 'ir.actions.act_window_close'}
		return result

class StockMove(models.Model):
	_inherit = 'stock.move'

	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			product_uom = self.env['uom.uom'].browse(int(vals.get('product_uom')))
			if vals.get('product_uom_qty'):
				if vals.get('product_uom_qty') < product_uom.rounding:
					raise UserError(f"{vals.get('name')}\nCan't set Demand less than [{product_uom.rounding}] Rounding Precision on Unit: {product_uom.name}")
		result = super(StockMove, self).create(vals_list)
		return result

	def write(self, vals):
		if vals.get('product_uom_qty'):
			if vals.get('product_uom_qty') < self.product_uom.rounding:
				raise UserError(f"{self.name}\nCan't set Demand less than [{self.product_uom.rounding}] Rounding Precision on Unit: {self.product_uom.name}")
		if vals.get('quantity'):
			if vals.get('quantity') < self.product_uom.rounding:
				raise UserError(f"{self.name}\nCan't set Quantity less than [{self.product_uom.rounding}] Rounding Precision on Unit: {self.product_uom.name}")
		result = super(StockMove, self).write(vals)
		return result