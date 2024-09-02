# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class BpDeposit(models.Model):
	_name = 'bp.deposit'
	__description = 'Bp Deposit'

	name = fields.Char('Name')
	partner_id = fields.Many2one('res.partner','Customer')
	total = fields.Float('Total')
	image = fields.Binary('Image')
	date = fields.Datetime('Date')
	user_id = fields.Many2one('res.users','Approval')
	state = fields.Selection([
		('check','Check'),
		('done','Done'),
		('cancel','Cancel')
	], string='Status')

	def action_confirm(self):
		if self.state == 'cancel':
			raise ValidationError(_('Status Cancel tidak dapat di Konfirmasi.'))
		if not self.partner_id:
			raise ValidationError(_('Customer harus di isi.'))
		if not self.image:
			raise ValidationError(_('Foto bukti transfer tidak ada.'))
		total_deposit_now = self.partner_id.total_deposit
		total_deposit_now += self.total
		self.partner_id.write({'total_deposit': total_deposit_now})
		self.state = 'done'
		self.user_id = self.env.user.id

	def action_cancel(self):
		if not self.partner_id:
			raise ValidationError(_('Customer harus di isi.'))
		if self.state == 'done':
			total_deposit_now = self.partner_id.total_deposit
			total_deposit_now -= self.total
			self.partner_id.write({'total_deposit': total_deposit_now})
			self.state = 'cancel'
			self.user_id = self.env.user.id
		else:
			self.state = 'cancel'

	def action_to_check(self):
		if not self.partner_id:
			raise ValidationError(_('Customer harus di isi.'))
		self.state = 'check'

