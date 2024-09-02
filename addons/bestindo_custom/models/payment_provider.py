# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class PaymentProvider(models.Model):
	_inherit = 'payment.provider'

	partner_id = fields.Many2one('res.partner','Partner')
	bp_journal_id = fields.Many2one('account.journal','Journal')
	is_deposit = fields.Boolean('Deposit')
	is_credit = fields.Boolean('Credit')
	is_bank = fields.Boolean('Bank')
	is_cod = fields.Boolean('COD')
	acc_name = fields.Char('Account Name')
	acc_number = fields.Char('Account Number')
	description = fields.Text('Description')

	@api.model
	def default_get(self, fields):
		result = super(PaymentProvider, self).default_get(fields)
		result.update(code='custom',state='enabled',custom_mode='wire_transfer',is_published=True)
		return result
