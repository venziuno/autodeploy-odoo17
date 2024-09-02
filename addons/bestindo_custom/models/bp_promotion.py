# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class BpPromotion(models.Model):
	_name = 'bp.promotion'
	_description = 'BP Promotion'

	name = fields.Char('Voucher Name')
	image = fields.Binary('Banner')
	disc_flat = fields.Float('Discount Flat')
	disc_percent = fields.Float('Discount (%)')
	is_all_product = fields.Boolean('Apply to All Product')
	product_ids = fields.One2many('product.product','bp_promotion_id','Product')
	line_ids = fields.One2many('bp.promotion.line','promotion_id','Line')
	start_date = fields.Datetime('Start')
	end_date = fields.Datetime('End')

class BpPromotionLine(models.Model):
	_name = 'bp.promotion.line'
	_description = 'BP Promotion Line'

	promotion_id = fields.Many2one('bp.promotion','Promotion')
	product_id = fields.Many2one('product.product','Product')
	disc_flat = fields.Float('Discount Flat')
	disc_percent = fields.Float('Discount (%)')