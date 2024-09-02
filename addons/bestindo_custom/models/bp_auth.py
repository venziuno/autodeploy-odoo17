# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class BpAuth(models.Model):
	_name = 'bp.auth'
	_description = 'Bp Authorization'

	name = fields.Char('Name')
	roles_id = fields.Many2one('bp.users.roles','Roles')
	model_id = fields.Many2one('ir.model','Table')
	menu_id = fields.Many2one('ir.ui.menu','Menu')
	group_id = fields.Many2one('res.groups','Group')
	perm_read = fields.Boolean('Read')
	perm_write = fields.Boolean('Write')
	perm_create = fields.Boolean('Create')
	perm_unlink = fields.Boolean('Delete')

