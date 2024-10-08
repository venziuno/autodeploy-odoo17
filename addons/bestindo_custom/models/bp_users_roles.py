# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class BpUsersRoles(models.Model):
	_name = 'bp.users.roles'
	_description = 'Bp Users Roles'

	name = fields.Char('Roles')
	is_dashboard = fields.Boolean('Dashboards')
	is_delivery = fields.Boolean('Delivery Orders')
	is_product = fields.Boolean('Products')
	is_promotion = fields.Boolean('Promotions')
	is_user = fields.Boolean('Users')
	is_deposit = fields.Boolean('Deposit')
	is_transaction = fields.Boolean('Transactions')
	is_setting = fields.Boolean('Settings')
	group_id = fields.Many2one('res.groups','Group')

	auth_ids = fields.One2many('bp.auth','roles_id','Authorization Menu')

	def auto_set_master_roles(self):
		master_role = self.env['bp.users.roles'].search([('name','=','Master')], limit=1)
		user = self.env['res.users'].browse(2)
		user.roles_id = master_role.id
		return True

	@api.model
	def create(self, vals):
		context = self.env.context
		result = super(BpUsersRoles, self.with_context(context)).create(vals)

		if 'is_dashboard' in vals:
			dashboard = self.env.ref('spreadsheet_dashboard.spreadsheet_dashboard_menu_root')
			if vals.get('is_dashboard'):
				dashboard.write({'groups_id': [(4, result.group_id.id, 0)]})
			else:
				dashboard.write({'groups_id': [(3, result.group_id.id, 0)]})

		if 'is_delivery' in vals:
			delivery = self.env.ref('stock.menu_stock_root')
			if vals.get('is_delivery'):
				delivery.write({'groups_id': [(4, result.group_id.id, 0)]})
			else:
				delivery.write({'groups_id': [(3, result.group_id.id, 0)]})

		if 'is_product' in vals:
			product = self.env.ref('bestindo_custom.products_menu_bp_custom')
			if vals.get('is_product'):
				product.write({'groups_id': [(4, result.group_id.id, 0)]})
			else:
				product.write({'groups_id': [(3, result.group_id.id, 0)]})

		if 'is_promotion' in vals:
			promotion = self.env.ref('bestindo_custom.promotion_menu_bp_custom')
			if vals.get('is_promotion'):
				promotion.write({'groups_id': [(4, result.group_id.id, 0)]})
			else:
				promotion.write({'groups_id': [(3, result.group_id.id, 0)]})

		if 'is_user' in vals:
			user = self.env.ref('contacts.menu_contacts')
			if vals.get('is_user'):
				user.write({'groups_id': [(4, result.group_id.id, 0)]})
			else:
				user.write({'groups_id': [(3, result.group_id.id, 0)]})

		if 'is_deposit' in vals:
			deposit = self.env.ref('bestindo_custom.res_partner_menu_deposit')
			if vals.get('is_deposit'):
				deposit.write({'groups_id': [(4, result.group_id.id, 0)]})
			else:
				deposit.write({'groups_id': [(3, result.group_id.id, 0)]})

		if 'is_transaction' in vals:
			transaction = self.env.ref('sale.sale_menu_root')
			if vals.get('is_transaction'):
				transaction.write({'groups_id': [(4, result.group_id.id, 0)]})
			else:
				transaction.write({'groups_id': [(3, result.group_id.id, 0)]})

		if 'is_setting' in vals:
			setting = self.env.ref('bestindo_custom.bestindo_settings_menu_root')
			if vals.get('is_setting'):
				setting.write({'groups_id': [(4, result.group_id.id, 0)]})
			else:
				setting.write({'groups_id': [(3, result.group_id.id, 0)]})
		return result

	def write(self, vals):
		context = self.env.context
		result = super(BpUsersRoles, self.with_context(context)).write(vals)

		if 'is_dashboard' in vals:
			dashboard = self.env.ref('spreadsheet_dashboard.spreadsheet_dashboard_menu_root')
			if vals.get('is_dashboard'):
				dashboard.write({'groups_id': [(4, self.group_id.id, 0)]})
			else:
				dashboard.write({'groups_id': [(3, self.group_id.id, 0)]})

		if 'is_delivery' in vals:
			delivery = self.env.ref('stock.menu_stock_root')
			if vals.get('is_delivery'):
				delivery.write({'groups_id': [(4, self.group_id.id, 0)]})
			else:
				delivery.write({'groups_id': [(3, self.group_id.id, 0)]})

		if 'is_product' in vals:
			product = self.env.ref('bestindo_custom.products_menu_bp_custom')
			if vals.get('is_product'):
				product.write({'groups_id': [(4, self.group_id.id, 0)]})
			else:
				product.write({'groups_id': [(3, self.group_id.id, 0)]})

		if 'is_promotion' in vals:
			promotion = self.env.ref('bestindo_custom.promotion_menu_bp_custom')
			if vals.get('is_promotion'):
				promotion.write({'groups_id': [(4, self.group_id.id, 0)]})
			else:
				promotion.write({'groups_id': [(3, self.group_id.id, 0)]})

		if 'is_user' in vals:
			user = self.env.ref('contacts.menu_contacts')
			if vals.get('is_user'):
				user.write({'groups_id': [(4, self.group_id.id, 0)]})
			else:
				user.write({'groups_id': [(3, self.group_id.id, 0)]})

		if 'is_deposit' in vals:
			deposit = self.env.ref('bestindo_custom.res_partner_menu_deposit')
			if vals.get('is_deposit'):
				deposit.write({'groups_id': [(4, self.group_id.id, 0)]})
			else:
				deposit.write({'groups_id': [(3, self.group_id.id, 0)]})

		if 'is_transaction' in vals:
			transaction = self.env.ref('sale.sale_menu_root')
			if vals.get('is_transaction'):
				transaction.write({'groups_id': [(4, self.group_id.id, 0)]})
			else:
				transaction.write({'groups_id': [(3, self.group_id.id, 0)]})

		if 'is_setting' in vals:
			setting = self.env.ref('bestindo_custom.bestindo_settings_menu_root')
			if vals.get('is_setting'):
				setting.write({'groups_id': [(4, self.group_id.id, 0)]})
			else:
				setting.write({'groups_id': [(3, self.group_id.id, 0)]})

		return result