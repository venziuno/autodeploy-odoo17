# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class BpNegotiation(models.Model):
	_name = 'bp.negotiation'
	_description = 'Bp Negotiation'

	name = fields.Char('Name')
	sale_id = fields.Many2one('sale.order','Transaction')
	partner_id = fields.Many2one('res.partner','Customer')
	message = fields.Text('Message')
	date = fields.Datetime('Date')
	state = fields.Selection([
		('draft','Draft'),
		('check','Checking'),
		('done','Done'),
		('cancel','Cancel'),
	], string='State', default='draft')
	line_ids = fields.One2many('bp.negotiation.line','negotiation_id','Line')

	@api.onchange('sale_id')
	def onchange_sale_id(self):
		if self.sale_id:
			self.name = self.sale_id.name

	def action_draft(self):
		for rec in self:
			rec.state = 'draft'

	def action_done(self):
		for rec in self:
			# if not rec.line_ids:
			# 	raise ValidationError(('Products perlu di isi!'))
			if not rec.message:
				raise ValidationError(('Message perlu di isi!'))
			rec.state = 'done'

	def action_cancel(self):
		for rec in self:
			rec.state = 'cancel'

	def action_to_check(self):
		for rec in self:
			rec.state = 'check'

class BpNegotiationLine(models.Model):
	_name = 'bp.negotiation.line'
	_description = 'Bp Negotiation Line'

	negotiation_id = fields.Many2one('bp.negotiation','Negotiation')
	product_id = fields.Many2one('product.product','Product')
	message = fields.Char('Message')
