# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	point_type = fields.Selection([
		('flat','Flat'),
		('percent','Percentage')
	], string='Point Type')
	flat_point = fields.Float('Flat Point')
	percent_point = fields.Float('Percentage Point')
	segment_ids = fields.Many2many('product.segment','bp_prod_segment_rel','segment_id','product_tmpl_id','Segment')
	product_image_ids = fields.One2many('bp.product.image', 'product_tmpl_id', 'Images')
	attachment_id = fields.Many2one('ir.attachment', 'Attachments')
	upload_product_image_ids = fields.Many2many('ir.attachment', 'res_ir_attachment_relation','res_id', 'attachment_id', string="Upload")

	@api.model
	def default_get(self, fields):
		result = super(ProductTemplate, self).default_get(fields)
		result['detailed_type'] = 'consu'
		result['invoice_policy'] = 'order'
		return result

	@api.model
	def create(self, vals):
		context = self.env.context
		result = super(ProductTemplate, self.with_context(context)).create(vals)
		if vals.get('upload_product_image_ids'):
			for x in vals.get('upload_product_image_ids'):
				if x[0] == 4:
					attachment_id = self.env['ir.attachment'].browse(x[1])
					if attachment_id.datas:
						self.env['bp.product.image'].create({
							'image_id': x[1],
							'image': attachment_id.datas,
							'name': attachment_id.name,
							'product_tmpl_id': result.id
						})
				if x[0] == 3:
					bp_img_id = self.env['bp.product.image'].search([('image_id','=',x[1])]).unlink()

		return result

	def write(self, vals):
		context = self.env.context
		result = super(ProductTemplate, self.with_context(context)).write(vals)
		if vals.get('upload_product_image_ids'):
			for x in vals.get('upload_product_image_ids'):
				if x[0] == 4:
					attachment_id = self.env['ir.attachment'].browse(x[1])
					if attachment_id.datas:
						self.env['bp.product.image'].create({
							'image_id': x[1],
							'image': attachment_id.datas,
							'name': attachment_id.name,
							'product_tmpl_id': self.id
						})
				if x[0] == 3:
					bp_img_id = self.env['bp.product.image'].search([('image_id','=',x[1])]).unlink()

		return result

class ProductProduct(models.Model):
	_inherit = 'product.product'

	bp_promotion_id = fields.Many2one('bp.promotion','Promotion')
	product_var_image_ids = fields.One2many('bp.product.image.variant', 'product_id', 'Variant Images')
	attachment_id = fields.Many2one('ir.attachment', 'Attachments')
	upload_product_var_image_ids = fields.Many2many('ir.attachment', 'res_bp_var_ir_attachment_relation','res_id', 'attachment_id', string="Upload")

	@api.model
	def create(self, vals):
		context = self.env.context
		result = super(ProductProduct, self.with_context(context)).create(vals)
		if vals.get('upload_product_var_image_ids'):
			for x in vals.get('upload_product_var_image_ids'):
				if x[0] == 4:
					attachment_id = self.env['ir.attachment'].browse(x[1])
					if attachment_id.datas:
						self.env['bp.product.image.variant'].create({
							'image_id': x[1],
							'image': attachment_id.datas,
							'name': attachment_id.name,
							'product_id': result.id
						})
				if x[0] == 3:
					bp_img_id = self.env['bp.product.image.variant'].search([('image_id','=',x[1])]).unlink()

		return result

	def write(self, vals):
		context = self.env.context
		result = super(ProductProduct, self.with_context(context)).write(vals)
		if vals.get('upload_product_var_image_ids'):
			for x in vals.get('upload_product_var_image_ids'):
				if x[0] == 4:
					attachment_id = self.env['ir.attachment'].browse(x[1])
					if attachment_id.datas:
						self.env['bp.product.image.variant'].create({
							'image_id': x[1],
							'image': attachment_id.datas,
							'name': attachment_id.name,
							'product_id': self.id
						})
				if x[0] == 3:
					bp_img_id = self.env['bp.product.image.variant'].search([('image_id','=',x[1])]).unlink()

		return result

class ProductCategory(models.Model):
	_inherit = 'product.category'

	partner_id = fields.Many2one('res.partner','Partner')
	active = fields.Boolean('Active', default='True')

class ProductSegment(models.Model):
	_name = 'product.segment'
	_description = 'Product Segment'

	partner_id = fields.Many2one('res.partner','Partner')
	name = fields.Char('Name')
	product_tmpl_id = fields.Many2one('product.template','Product Template')
	product_count = fields.Integer(
		'# Products', compute='_compute_product_count',
		help="The number of products under this segment")
	active = fields.Boolean('Active', default='True')

	def _compute_product_count(self):
		for seg in self:
			product_count = 0
			segment = self.env['product.template'].search([('segment_ids','in',seg.id)])
			seg.product_count = len(segment)

class BpProductImage(models.Model):
	_name = 'bp.product.image'
	_description = 'Bp Product Image'

	name = fields.Char(string="Description")
	image = fields.Binary(string="Image", attachment=True)
	product_tmpl_id = fields.Many2one('product.template', string="Product Template")
	image_id = fields.Integer('Image ID')

	def unlink(self):
		for dels in self:
			attachment_id = self.env['ir.attachment'].browse(dels.image_id)
			if attachment_id.datas:
				attachment_id.unlink()
		return super(BpProductImage, self).unlink()

class BpProductImageVariant(models.Model):
	_name = 'bp.product.image.variant'
	_description = 'Bp Product Image Variant'

	name = fields.Char(string="Description")
	image = fields.Binary(string="Image", attachment=True)
	product_id = fields.Many2one('product.product', string="Product Variant")
	image_id = fields.Integer('Image ID')

	def unlink(self):
		for dels in self:
			attachment_id = self.env['ir.attachment'].browse(dels.image_id)
			if attachment_id.datas:
				attachment_id.unlink()
		return super(BpProductImageVariant, self).unlink()