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
	is_transaction = fields.Boolean('Transactions')
	is_setting = fields.Boolean('Settings')

	@api.model
	def create(self, vals):
		context = self.env.context
		result = super(BpUsersRoles, self.with_context(context)).create(vals)
		return result

	def write(self, vals):
		context = self.env.context
		result = super(BpUsersRoles, self.with_context(context)).write(vals)
		return result