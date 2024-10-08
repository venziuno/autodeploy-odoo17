# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
from datetime import time, timedelta
from odoo.tools import float_round

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	point_type = fields.Selection([
		('flat','Flat'),
		('percent','Percentage')
	], string='Point Type')
	prod_type = fields.Selection([
		('vacuum','Vacuum'),
		('soap','Soap'),
		('machine','Machine'),
		('other','Other')
	], string='Product Type', default='other')
	flat_point = fields.Float('Flat Point')
	percent_point = fields.Float('Percentage Point')
	segment_ids = fields.Many2many('product.segment','bp_prod_segment_rel','segment_id','product_tmpl_id','Segment')
	product_image_ids = fields.One2many('bp.product.image', 'product_tmpl_id', 'Images')
	attachment_id = fields.Many2one('ir.attachment', 'Attachments')
	upload_product_image_ids = fields.Many2many('ir.attachment', 'res_ir_attachment_relation','res_id', 'attachment_id', string="Upload")
	last_price = fields.Float('Last Price')


	@api.model
	def default_get(self, fields):
		result = super(ProductTemplate, self).default_get(fields)
		result['detailed_type'] = 'consu'
		result['invoice_policy'] = 'order'
		return result

	@api.onchange('categ_id')
	def onchange_categ_id(self):
		if self.categ_id:
			self.segment_ids = [(6, 0, self.categ_id.segment_ids.ids)]

	@api.model
	def create(self, vals):
		context = self.env.context
		if vals.get('list_price'):
			if vals.get('list_price') < 0.0 :
				vals['list_price'] = 0.0
		if vals.get('flat_point'):
			if vals.get('flat_point') < 0.0 :
				vals['flat_point'] = 0.0
		if vals.get('percent_point'):
			if vals.get('percent_point') < 0.0 :
				vals['percent_point'] = 0.0

		result = super(ProductTemplate, self.with_context(context)).create(vals)
		# if vals.get('upload_product_image_ids'):
		# 	for x in vals.get('upload_product_image_ids'):
		# 		if x[0] == 4:
		# 			attachment_id = self.env['ir.attachment'].browse(x[1])
		# 			if attachment_id.datas:
		# 				self.env['bp.product.image'].create({
		# 					'image_id': x[1],
		# 					'image': attachment_id.datas,
		# 					'name': attachment_id.name,
		# 					'product_tmpl_id': result.id
		# 				})
		# 		if x[0] == 3:
		# 			bp_img_id = self.env['bp.product.image'].search([('image_id','=',x[1])]).unlink()

		if vals.get('point_type') or vals.get('flat_point') or vals.get('percent_point'):
			if result.point_type:
				if result.point_type == 'flat':
					result.product_variant_ids.write({
						'point_type': 'flat',
						'flat_point': result.flat_point,
					})
				elif result.point_type == 'percent':
					result.product_variant_ids.write({
						'point_type': 'percent',
						'percent_point': result.percent_point,
					})
		
		if vals.get('list_price'):
			vals['last_price'] = result.list_price

		return result

	def write(self, vals):
		context = self.env.context
		if vals.get('list_price'):
			vals['last_price'] = self.list_price
		if vals.get('list_price'):
			if vals.get('list_price') < 0.0 :
				vals['list_price'] = 0.0
		if vals.get('flat_point'):
			if vals.get('flat_point') < 0.0 :
				vals['flat_point'] = 0.0
		if vals.get('percent_point'):
			if vals.get('percent_point') < 0.0 :
				vals['percent_point'] = 0.0

		result = super(ProductTemplate, self.with_context(context)).write(vals)
		# if vals.get('upload_product_image_ids'):
		# 	for x in vals.get('upload_product_image_ids'):
		# 		if x[0] == 4:
		# 			attachment_id = self.env['ir.attachment'].browse(x[1])
		# 			if attachment_id.datas:
		# 				self.env['bp.product.image'].create({
		# 					'image_id': x[1],
		# 					'image': attachment_id.datas,
		# 					'name': attachment_id.name,
		# 					'product_tmpl_id': self.id
		# 				})
		# 		if x[0] == 3:
		# 			bp_img_id = self.env['bp.product.image'].search([('image_id','=',x[1])]).unlink()

		if vals.get('point_type') or vals.get('flat_point') or vals.get('percent_point'):
			if self.point_type:
				if self.point_type == 'flat':
					self.product_variant_ids.write({
						'point_type': 'flat',
						'flat_point': self.flat_point,
					})
				elif self.point_type == 'percent':
					self.product_variant_ids.write({
						'point_type': 'percent',
						'percent_point': self.percent_point,
					})

		return result

	def action_bp_open_variants(self):
		return {
			'type': 'ir.actions.act_window',
			'name': 'Product Variants',
			'res_model': 'product.product',
			'view_mode': 'tree,form',
			'domain': [('id','in',self.product_variant_ids.ids)],
			'target': 'current',
		}

class ProductProduct(models.Model):
	_inherit = 'product.product'

	point_type = fields.Selection([
		('flat','Flat'),
		('percent','Percentage')
	], string='Point Type')
	prod_type = fields.Selection([
		('vacuum','Vacuum'),
		('soap','Soap'),
		('machine','Machine'),
		('other','Other')
	], string='Product Type', default='other')
	flat_point = fields.Float('Flat Point')
	percent_point = fields.Float('Percentage Point')
	bp_promotion_id = fields.Many2one('bp.promotion','Promotion')
	product_var_image_ids = fields.One2many('bp.product.image.variant', 'product_id', 'Variant Images')
	attachment_id = fields.Many2one('ir.attachment', 'Attachments')
	upload_product_var_image_ids = fields.Many2many('ir.attachment', 'res_bp_var_ir_attachment_relation','res_id', 'attachment_id', string="Upload")
	list_price = fields.Float(
		'Sales Price', default=1.0,
		digits='Product Price',
		related='product_tmpl_id.list_price',
		store=True,
		help="Price at which the product is sold to customers.",
	)
	last_price = fields.Float('Last Price')

	def _compute_sales_count(self):
		r = {}
		self.sales_count = 0
		if not self.user_has_groups('sales_team.group_sale_salesman'):
			return r
		date_from = fields.Datetime.to_string(fields.datetime.combine(fields.datetime.now() - timedelta(days=365),
																	  time.min))

		# done_states = self.env['sale.report']._get_done_states()
		done_states = ['sale','done']

		domain = [
			('state', 'in', done_states),
			('product_id', 'in', self.ids),
			('date', '>=', date_from),
		]
		for product, product_uom_qty in self.env['sale.report']._read_group(domain, ['product_id'], ['product_uom_qty:sum']):
			r[product.id] = product_uom_qty
		for product in self:
			if not product.id:
				product.sales_count = 0.0
				continue
			product.sales_count = float_round(r.get(product.id, 0), precision_rounding=product.uom_id.rounding)
		return r

	@api.model
	def create(self, vals):
		context = self.env.context
		if vals.get('list_price'):
			if vals.get('list_price') < 0.0 :
				vals['list_price'] = 0.0
		if vals.get('flat_point'):
			if vals.get('flat_point') < 0.0 :
				vals['flat_point'] = 0.0
		if vals.get('percent_point'):
			if vals.get('percent_point') < 0.0 :
				vals['percent_point'] = 0.0
		result = super(ProductProduct, self.with_context(context)).create(vals)
		# if vals.get('upload_product_var_image_ids'):
		# 	for x in vals.get('upload_product_var_image_ids'):
		# 		if x[0] == 4:
		# 			attachment_id = self.env['ir.attachment'].browse(x[1])
		# 			if attachment_id.datas:
		# 				self.env['bp.product.image.variant'].create({
		# 					'image_id': x[1],
		# 					'image': attachment_id.datas,
		# 					'name': attachment_id.name,
		# 					'product_id': result.id
		# 				})
		# 		if x[0] == 3:
		# 			bp_img_id = self.env['bp.product.image.variant'].search([('image_id','=',x[1])]).unlink()
		if vals.get('list_price'):
			vals['last_price'] = result.list_price
		return result

	def write(self, vals):
		context = self.env.context
		if vals.get('list_price'):
			vals['last_price'] = self.list_price
		if vals.get('list_price'):
			if vals.get('list_price') < 0.0 :
				vals['list_price'] = 0.0
		if vals.get('flat_point'):
			if vals.get('flat_point') < 0.0 :
				vals['flat_point'] = 0.0
		if vals.get('percent_point'):
			if vals.get('percent_point') < 0.0 :
				vals['percent_point'] = 0.0
		result = super(ProductProduct, self.with_context(context)).write(vals)
		# if vals.get('upload_product_var_image_ids'):
		# 	for x in vals.get('upload_product_var_image_ids'):
		# 		if x[0] == 4:
		# 			attachment_id = self.env['ir.attachment'].browse(x[1])
		# 			if attachment_id.datas:
		# 				self.env['bp.product.image.variant'].create({
		# 					'image_id': x[1],
		# 					'image': attachment_id.datas,
		# 					'name': attachment_id.name,
		# 					'product_id': self.id
		# 				})
		# 		if x[0] == 3:
		# 			bp_img_id = self.env['bp.product.image.variant'].search([('image_id','=',x[1])]).unlink()
		
		return result

class ProductCategory(models.Model):
	_inherit = 'product.category'

	partner_id = fields.Many2one('res.partner','Partner')
	icon_img = fields.Binary('Image')
	segment_ids = fields.Many2many('product.segment','bp_prod_categ_segment_relation','segment_id','category_id','Segment')
	segment_id = fields.Many2one('product.segment','Segments')
	active = fields.Boolean('Active', default='True')

class ProductSegment(models.Model):
	_name = 'product.segment'
	_description = 'Product Segment'

	partner_id = fields.Many2one('res.partner','Partner')
	category_id = fields.Many2one('product.category','Category')
	icon_img = fields.Binary('Image')
	name = fields.Char('Name')
	product_tmpl_id = fields.Many2one('product.template','Product Template')
	product_count = fields.Integer(
		'# Products', compute='_compute_product_count',
		help="The number of products under this segment")
	active = fields.Boolean('Active', default='True')
	color = fields.Char(string='Color Index')

	def _compute_product_count(self):
		for seg in self:
			product_count = 0
			segment = self.env['product.template'].search([('segment_ids','in',seg.id)])
			seg.product_count = len(segment)

class BpProductImage(models.Model):
	_name = 'bp.product.image'
	_description = 'Bp Product Image'

	name = fields.Char(string="Description")
	image = fields.Binary(string="Image")
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

class BpFavoriteProduct(models.Model):
	_name = 'bp.favorite.product'
	_description = 'Bp Favorite Product'

	name = fields.Char('Name')
	image = fields.Binary('Image', related='product_id.image_1920')
	product_id = fields.Many2one('product.product','Product')
	partner_id = fields.Many2one('res.partner','Customer')

	# @api.onchange('product_id')
	# def onchange_product_id(self):
	# 	if self.product_id:
	# 		self.image = self.product_id.image_1920

	# @api.model
	# def create(self, vals):
	# 	context = self.env.context
	# 	result = super(BpFavoriteProduct, self.with_context(context)).create(vals)
	# 	if result.product_id:
	# 		result.image = result.product_id.image_1920
	# 	return result

	# def write(self, vals):
	# 	context = self.env.context
	# 	result = super(BpFavoriteProduct, self.with_context(context)).write(vals)
	# 	if vals.get('product_id',False):
	# 		product_id = self.env['product.product'].browse(vals.get('product_id',False))
	# 		if product_id:
	# 			vals['image'] = product_id.image_1920
	# 	return result