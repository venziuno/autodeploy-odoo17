# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class BpCart(models.Model):
	_name = 'bp.cart'
	_description = 'Bp Cart'

	name = fields.Char('Name')
	order_id = fields.Many2one('sale.order','Order')
	product_id = fields.Many2one('product.product','Product')
	product_uom_qty = fields.Float('Quantity')
	partner_id = fields.Many2one('res.partner','Partner')
	state = fields.Selection('State', related='order_id.state', store=True)

	

