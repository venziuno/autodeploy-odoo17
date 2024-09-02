# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class ResCompany(models.Model):
	_inherit = 'res.company'

	token_api = fields.Char('Token API')

	def create_token_api(self):
		uuid_str = str(uuid.uuid4())
		self.token_api = uuid_str