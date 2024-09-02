# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class PaymentProvider(models.Model):
	_inherit = 'payment.provider'

	partner_id = fields.Many2one('res.partner','Partner')
