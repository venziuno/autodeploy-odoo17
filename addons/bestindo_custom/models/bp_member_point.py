# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class BpMemberPoint(models.Model):
	_name = 'bp.member.point'
	_description = 'Bp Member Point'

	name = fields.Char('Name')
	date = fields.Datetime('Date')
	sale_id = fields.Many2one('sale.order','Order')
	point = fields.Integer('Point')
	partner_id = fields.Many2one('res.partner','Partner')
	product_id = fields.Many2one('product.product','Product')
	product_tmpl_id = fields.Many2one('product.template','Product Template')
