# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class ResUsers(models.Model):
	_inherit = 'res.users'

	roles_id = fields.Many2one('bp.users.roles','Roles')
	bp_groups_id = fields.Many2one('res.groups','Bp Groups')

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
		return result

	def write(self, vals):
		context = self.env.context
		if vals.get('roles_id',False):
			if self.roles_id:
				if self.roles_id.name == 'Master':
					groups_xml_id = 'bestindo_custom.group_master_bestindo_custom'
				elif self.roles_id.name == 'Admin':
					groups_xml_id = 'bestindo_custom.group_admin_bestindo_custom'
				else:
					groups_xml_id = 'bestindo_custom.group_driver_bestindo_custom'
				if self.has_group(groups_xml_id):
					self.bp_groups_id.write({'users': [(3, self.id, 0)]})
		result = super(ResUsers, self.with_context(context)).write(vals)
		if vals.get('roles_id',False):
			bp_groups_id = self.env['res.groups'].browse(vals.get('bp_groups_id',False))
			if bp_groups_id:
				bp_groups_id.write({'users': [(4, self.id, 0)]})

		return result
