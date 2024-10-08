# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class ResUsers(models.Model):
	_inherit = 'res.users'

	roles_id = fields.Many2one('bp.users.roles','Roles')
	bp_groups_id = fields.Many2one('res.groups','Bp Groups')
	token_api = fields.Char('Token API')

	@api.onchange('roles_id')
	def onchange_roles_id(self):
		if self.roles_id:
			domain = []
			if self.roles_id.name == 'Master':
				domain = [('name','=','Master - Bestindo Group')]
			if self.roles_id.name == 'Admin':
				domain = [('name','=','Admin - Bestindo Group')]
			if self.roles_id.name == 'Driver':
				domain = [('name','=','Driver - Bestindo Group')]
			bp_groups_id = self.env['res.groups'].search(domain, limit=1)
			self.bp_groups_id = bp_groups_id.id

	@api.model
	def create(self, vals):
		context = self.env.context
		result = super(ResUsers, self.with_context(context)).create(vals)
		if vals.get('roles_id',False):
			result.bp_groups_id.write({'users': [(4, result.id, 0)]})
		if result.roles_id.name == 'Driver':
			result.partner_id.write({'user_type': 'driver'})
		if result.roles_id.name == 'Master':
			group_erp_manager = self.env.ref('base.group_erp_manager')
			if group_erp_manager:
				group_erp_manager.write({'users': [(4, result.id, 0)]})
		return result

	def write(self, vals):
		context = self.env.context
		if context.get('is_driver'):
			result = super(ResUsers, self.with_context(context)).write(vals)
		if vals.get('roles_id',False):
			if self.roles_id:
				if self.roles_id.name == 'Master':
					groups_xml_id = 'bestindo_custom.group_master_bestindo_custom'
					group_erp_manager = self.env.ref('base.group_erp_manager')
					if group_erp_manager:
						group_erp_manager.write({'users': [(4, self.id, 0)]})
				elif self.roles_id.name == 'Admin':
					groups_xml_id = 'bestindo_custom.group_admin_bestindo_custom'
				else:
					groups_xml_id = 'bestindo_custom.group_driver_bestindo_custom'
				if self.has_group(groups_xml_id):
					self.bp_groups_id.write({'users': [(3, self.id, 0)]})
		if not context.get('is_driver'):
			result = super(ResUsers, self.with_context(context)).write(vals)
		if vals.get('roles_id',False):
			bp_groups_id = self.env['res.groups'].browse(vals.get('bp_groups_id',False))
			if not bp_groups_id:
				bp_groups_id = self.roles_id.group_id
			if bp_groups_id:
				bp_groups_id.write({'users': [(4, self.id, 0)]})
		return result

	def create_token_api(self):
		uuid_str = str(uuid.uuid4())
		self.token_api = uuid_str
