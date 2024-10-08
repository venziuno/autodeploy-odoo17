# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class MultiLocation(models.Model):
	_name = 'multi.location'
	_description = 'Multi Location'

	name = fields.Char('Name')
	full_address = fields.Char(compute='_full_address',string='Address')
	street = fields.Char('Street')
	city = fields.Char('City')
	zip = fields.Char('Zip')
	partner_id = fields.Many2one('res.partner','Partner')
	state_id = fields.Many2one('res.country.state','State')
	country_id = fields.Many2one('res.country','Country')

	@api.onchange('state_id')
	def onchange_state_id(self):
		if self.state_id.country_id:
			self.country_id = self.state_id.country_id.id

	def _full_address(self):
		for record in self:
			record.full_address = f"{record.street or ''},{record.city or ''},{record.state_id.name or ''},{record.zip or ''},{record.country_id.name or ''}"