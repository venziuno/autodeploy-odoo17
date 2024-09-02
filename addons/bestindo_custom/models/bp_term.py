# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class BpTerm(models.Model):
	_name = 'bp.term'
	_description = 'Bp Term'

	name = fields.Char('Name')
	description = fields.Text('Description')

