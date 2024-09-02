# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class BpPromotion(models.Model):
	_name = 'bp.promotion'
	_description = 'BP Promotion'

	name = fields.Char('Promotion Name')
	image = fields.Binary('Banner')
	disc_type = fields.Selection([
		('flat','Flat'),
		('percent','Percentage')
	],string='Discount Type', default='flat')
	disc_flat = fields.Float('Discount Flat')
	disc_percent = fields.Float('Discount (%)')
	is_all_product = fields.Boolean('Apply to All Product')
	product_ids = fields.One2many('product.product','bp_promotion_id','Product')
	line_ids = fields.One2many('bp.promotion.line','promotion_id','Line')
	start_date = fields.Datetime('Start')
	end_date = fields.Datetime('End')
	state = fields.Selection([
		('close','Close'),
		('open','Open')
	],string='State', default='close')
	description = fields.Text('Description')

	def action_open(self):
		for rec in self:
			if rec.line_ids or rec.is_all_product:
				rec.state = 'open'
			else:
				raise ValidationError(_('Product mohon di isi atau di terapkan ke semua Product.'))

	def action_close(self):
		for rec in self:
			rec.state = 'close'

	@api.model
	def create(self, vals):
		context = self.env.context
		if 'is_all_product' in vals:
			if vals.get('is_all_product'):
				promotion_id = self.search([('is_all_product','=',True)])
				if promotion_id:
					raise ValidationError(_(f'Apply to All Product sudah digunakan pada Promotion [{promotion_id.name}]'))
		result = super(BpPromotion, self.with_context(context)).create(vals)
		return result

	def write(self, vals):
		context = self.env.context
		if 'is_all_product' in vals:
			if vals.get('is_all_product'):
				promotion_id = self.search([('is_all_product','=',True)])
				if promotion_id:
					raise ValidationError(_(f'Apply to All Product sudah digunakan pada Promotion [{promotion_id.name}]'))
		result = super(BpPromotion, self.with_context(context)).write(vals)
		return result

class BpPromotionLine(models.Model):
	_name = 'bp.promotion.line'
	_description = 'BP Promotion Line'

	promotion_id = fields.Many2one('bp.promotion','Promotion')
	product_id = fields.Many2one('product.product','Product')
	disc_flat = fields.Float('Discount Flat')
	disc_percent = fields.Float('Discount (%)')

	@api.model
	def create(self, vals):
		context = self.env.context
		if vals.get('product_id'):
			product_id = self.search([('product_id','=',vals.get('product_id')),('promotion_id.is_all_product','=',False)])
			if product_id:
				raise ValidationError(_(f'Product sudah digunakan pada Promotion [{product_id.promotion_id.name}]'))
		result = super(BpPromotionLine, self.with_context(context)).create(vals)
		return result

	def write(self, vals):
		context = self.env.context
		if vals.get('product_id'):
			product_id = self.search([('product_id','=',vals.get('product_id')),('promotion_id.is_all_product','=',False)])
			if product_id:
				raise ValidationError(_(f'Product sudah digunakan pada Promotion [{product_id.promotion_id.name}]'))
		result = super(BpPromotionLine, self.with_context(context)).write(vals)
		return result