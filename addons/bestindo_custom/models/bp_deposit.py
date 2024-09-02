# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class BpDeposit(models.Model):
	_name = 'bp.deposit'
	_description = 'Bp Deposit'

	name = fields.Char('Transaction')
	partner_id = fields.Many2one('res.partner','Customer')
	total = fields.Float('Total')
	image = fields.Binary('Image')
	date = fields.Datetime('Date')
	user_id = fields.Many2one('res.users','Approval')
	state = fields.Selection([
		('check','Check'),
		('done','Done'),
		('cancel','Cancel'),
		('used','Used')
	], string='Status')
	reason = fields.Char('Reason Cancel')
	sale_id = fields.Many2one('sale.order','Sale Order')
	payment_id = fields.Many2one('payment.provider','Payment')

	@api.model
	def default_get(self, fields):
		result = super(BpDeposit, self).default_get(fields)
		context = self.env.context
		if context.get('active_model',False) == 'res.partner':
			result['partner_id'] = context.get('active_id',False)
		
		return result

	def action_confirm(self):
		if self.state == 'cancel':
			raise ValidationError(_('Status Cancel tidak dapat di Konfirmasi.'))
		if not self.partner_id:
			raise ValidationError(_('Customer harus di isi.'))
		if not self.image:
			raise ValidationError(_('Foto bukti transfer tidak ada.'))
		self.state = 'done'
		self.user_id = self.env.user.id

	def action_cancel(self):
		if not self.partner_id:
			raise ValidationError(_('Customer harus di isi.'))
		if self.state == 'done':
			total = self.total
			self.total = total*-1
			self.state = 'cancel'
			self.user_id = self.env.user.id
		else:
			self.state = 'cancel'

	def action_to_check(self):
		if not self.partner_id:
			raise ValidationError(_('Customer harus di isi.'))
		self.state = 'check'

