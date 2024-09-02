# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
#from validate_email import validate_email #pip install validate_email && pip install py3DNS

class ResPartner(models.Model):
	_inherit = 'res.partner'

	total_deposit = fields.Float('Total Deposit',compute='_compute_total_deposit')
	loyalty_point = fields.Integer('Loyalty Point')
	registration_id = fields.Char('Registration ID')
	payment_provider_ids = fields.Many2many('payment.provider','bp_payment_prov_relation','payment_id','partner_id','Payment Provider')
	password = fields.Char('Password')
	is_show_password = fields.Boolean('Show Password')
	multi_location_ids = fields.One2many('multi.location','partner_id','Multi Location')
	user_type = fields.Selection([
		('customer','Customer'),
		('driver', 'Driver')
	],'User Type', default='customer')

	is_another_address = fields.Boolean('Is Another Address')
	another_address_id = fields.Many2one('res.partner','Another Address')

	street_2nd = fields.Char('Street')
	city_2 = fields.Char('City')
	zip_2 = fields.Char('Zip')
	state_2_id = fields.Many2one('res.country.state','State')
	country_2_id = fields.Many2one('res.country','Country')

	full_address = fields.Char(compute="_full_address",string='Full Address 1')
	full_address2 = fields.Char(compute="_full_address",string='Full Address 2', tracking=True)
	partner_latitude2 = fields.Float('Latitude 2', digits=(10, 7))
	partner_longitude2 = fields.Float('Longitude 2', digits=(10, 7))

	point_count = fields.Integer('Point',compute='_compute_point_count')
	deposit_count = fields.Integer('Deposit')
	is_negotiation = fields.Boolean('Allow Negotiation', default=True)

	segment_ids = fields.Many2many('product.segment','bp_segment_relation','segment_id','partner_id','Segment')

	driver_id_no = fields.Char('ID Confirmation')
	driver_sim = fields.Char('No. SIM') 
	driver_merk = fields.Char('Merk Kendaraan')
	driver_type = fields.Char('Tipe Kendaraan')
	driver_no = fields.Char('No. Plat Kendaraan')
	driver_color = fields.Char('Warna Kendaraan')

	def _compute_total_deposit(self):
		for rec in self:
			deposit_ids = self.env['bp.deposit'].search([('partner_id','=',rec.id),('state','in',['done','used'])])
			total = sum(list(x.total for x in deposit_ids))
			rec.total_deposit = total

	def _compute_point_count(self):
		for rec in self:
			point_ids = self.env['bp.member.point'].search([('partner_id','=',rec.id)])
			point = sum(list(x.point for x in point_ids))
			rec.point_count = point

	@api.model
	def create(self, vals):
		context = self.env.context
		result = super(ResPartner, self.with_context(context)).create(vals)
		if vals.get('user_type','') == 'customer':
			if vals.get('street_2nd') or vals.get('city_2') or vals.get('state_2_id') or vals.get('zip_2') or vals.get('country_2_id') or vals.get('partner_latitude2') or vals.get('partner_longitude2'):
				another_address_id = self.create({
					'name': vals.get('name'),
					'user_type': vals.get('user_type'),
					'is_another_address': True,
					'another_address_id': result.id,
					'street': vals.get('street_2nd'),
					'city': vals.get('city_2'),
					'state_id': vals.get('state_2_id'),
					'zip': vals.get('zip_2'),
					'country_id': vals.get('country_2_id'),
					'partner_latitude': vals.get('partner_latitude2'),
					'partner_longitude': vals.get('partner_longitude2')
				})
				result.write({'another_address_id': another_address_id.id})
		return result

	def write(self, vals):
		context = self.env.context
		result = super(ResPartner, self.with_context(context)).write(vals)
		if self.user_type == 'customer':
			if vals.get('street_2nd') or vals.get('city_2') or vals.get('state_2_id') or vals.get('zip_2') or vals.get('country_2_id') or vals.get('partner_latitude2') or vals.get('partner_longitude2'):
				if self.another_address_id:
					self.another_address_id.write({
						'name': vals.get('name') or self.name,
						'user_type': vals.get('user_type') or self.user_type,
						'is_another_address': True,
						'street': vals.get('street_2nd') or self.street_2nd,
						'city': vals.get('city_2') or self.city_2,
						'state_id': vals.get('state_2_id') or self.state_2_id,
						'zip': vals.get('zip_2') or self.zip_2,
						'country_id': vals.get('country_2_id') or self.country_2_id,
						'partner_latitude': vals.get('partner_latitude2') or self.partner_latitude2,
						'partner_longitude': vals.get('partner_longitude2') or self.partner_longitude2
					})
				else:
					self.create({
						'name': vals.get('name') or self.name,
						'user_type': vals.get('user_type') or self.user_type,
						'another_address_id': self.id,
						'is_another_address': True,
						'street': vals.get('street_2nd') or self.street_2nd,
						'city': vals.get('city_2') or self.city_2,
						'state_id': vals.get('state_2_id') or self.state_2_id,
						'zip': vals.get('zip_2') or self.zip_2,
						'country_id': vals.get('country_2_id') or self.country_2_id,
						'partner_latitude': vals.get('partner_latitude2') or self.partner_latitude2,
						'partner_longitude': vals.get('partner_longitude2') or self.partner_longitude2
					})
		return result

	@api.onchange('state_2_id')
	def onchange_state_2_id(self):
		if self.state_2_id.country_id:
			self.country_2_id = self.state_2_id.country_id.id

	@api.model
	def default_get(self, fields):
		result = super(ResPartner, self).default_get(fields)
		context = self.env.context
		if context.get('is_driver',False):
			result['user_type'] = 'driver'
		else:
			result['user_type'] = 'customer'
		result['company_type'] = 'person'
		state_id = self.env['res.country.state'].search([('name','=','Kepulauan Riau')], limit=1)
		result['state_id'] = state_id.id
		result['state_2_id'] = state_id.id

		return result

	# @api.constrains('email')
	# def _check_email(self):
	# 	"""
	# 	Check the email is valid or not
	# 	"""
	# 	if self.email:
	# 		is_valid = validate_email(self.email, check_mx=False, verify=True,
	# 								  debug=False, smtp_timeout=10)
	# 		if is_valid is not True:
	# 			raise ValidationError(_('Anda hanya dapat menggunakan alamat email yang valid.'
	# 									'Alamat email “%s” tidak valid '
	# 									'atau tidak ada') % self.email)

	def action_view_history_point(self):
		ids = []
		partner_ids = self.search([('parent_id','=',self.id)])
		if partner_ids:
			ids = [x.id for x in partner_ids]
		action = {
			"type": "ir.actions.act_window",
			"view_mode": "tree,form",
			"name": _("Member Point"),
			"res_model": "bp.member.point",
			"domain": [('partner_id','in', [self.id]+ids)],
			"target": "current",
		}
		return action

	def action_view_history_deposit(self):
		ids = []
		partner_ids = self.search([('parent_id','=',self.id)])
		if partner_ids:
			ids = [x.id for x in partner_ids]
		action = {
			"type": "ir.actions.act_window",
			"view_mode": "tree,form",
			"name": _("Deposit"),
			"res_model": "bp.deposit",
			"domain": [('partner_id','in', [self.id]+ids)],
			"target": "current",
		}
		return action

	def action_view_driver_jobs(self):
		user_id = self.env['res.users'].search([('partner_id','=',self.id)])
		if not user_id:
			raise ValidationError(_('Tidak ada user untuk Driver ini.'))
		stock_ids = self.env['stock.picking'].search([('driver_id','=',user_id.id)])
		action = {
			"type": "ir.actions.act_window",
			"view_mode": "tree,form",
			"name": _("Delivery Orders"),
			"res_model": "stock.picking",
			"domain": [('id','in', stock_ids.ids)],
			'context': {'contact_display': 'partner_address', 'search_default_available': 1},
			"target": "current",
		}
		return action

	def action_view_favorite_products(self):
		fav_ids = self.env['bp.favorite.product'].search([('partner_id','=',self.id)])
		action = {
			"type": "ir.actions.act_window",
			"view_mode": "tree",
			"name": _("Favorite Products"),
			"res_model": "bp.favorite.product",
			"domain": [('id','in', fav_ids.ids)],
			"target": "current",
		}
		return action

	def create_users(self):
		search_email = self.search([('email','=',self.email),('id','!=',self.id)])
		if search_email:
			raise ValidationError(_('Email sudah digunakan oleh user lain.'))
		wizard_obj = self.env['portal.wizard']
		username = ''
		if '@' not in self.email:
			username = self.email
		wizard_id = wizard_obj.create({
			'user_ids': [(0, 0, {
				'partner_id': self.id,
				'email': self.email if '@' in self.email else f"{self.email}@bestindo.com"
			})]
		})
		wizard_id.user_ids.action_grant_access()
		if not self.password:
			raise UserError(_('Password mohon di isi.'))

		user_values = {'password': self.password}
		if username:
			user_values['login'] = username
			self.email = username
		self.user_ids.write(user_values)

		if self.user_type == 'driver':
			roles_id = self.env['bp.users.roles'].search([('name','=','Driver')], limit=1)
			internal_group = self.env.ref('base.group_user')
			sales_group = self.env.ref('sales_team.group_sale_manager')
			inventory_group = self.env.ref('stock.group_stock_manager')
			invoicing_group = self.env.ref('account.group_account_manager')

			group_ids = [internal_group.id,sales_group.id,inventory_group.id,invoicing_group.id]
			self.user_ids.with_context(is_driver=True).write({
				'groups_id': [(6, 0, group_ids)],
				'roles_id': roles_id.id,
			})
		return True

	def _full_address(self):
		for record in self:
			address_parts = [record.street, record.city, record.state_id.name, record.zip, record.country_id.name]
			record.full_address = ", ".join(filter(None, address_parts))

			address_parts_2 = [record.street_2nd, record.city_2, record.state_2_id.name, record.zip_2, record.country_2_id.name]
			record.full_address2 = ", ".join(filter(None, address_parts_2))

