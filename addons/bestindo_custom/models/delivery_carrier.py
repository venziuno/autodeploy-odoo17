# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class DeliveryCarrier(models.Model):
	_inherit = 'delivery.carrier'

	ongkir_ids = fields.One2many('bp.ongkir', 'carrier_id', 'Ongkir')
	is_cod = fields.Boolean('COD')

	@api.model
	def default_get(self, fields):
		ongkir_id = self.env.company.ongkir_product_id.id
		result = super(DeliveryCarrier, self).default_get(fields)
		result['product_id'] = ongkir_id
		return result

	def total_ongkir(self, amount_total):
		ongkir = 0
		if self.is_cod:
			return ongkir
		else:
			ongkir_id = self.env['bp.ongkir'].search([
				('carrier_id', '=', self.id),
				('total_from', '<=', amount_total),
				'|',
				('total_to', '>=', amount_total),
				('total_to', '=', 0)
			], limit=1, order='total_from asc')
			
			if ongkir_id:
				ongkir = ongkir_id.total
			
			return ongkir

	
class BpOngkir(models.Model):
	_name = 'bp.ongkir'
	_description = 'Bp Ongkir'

	total_from = fields.Float('From')
	total_to = fields.Float('To')
	total = fields.Float('Ongkir')
	carrier_id = fields.Many2one('delivery.carrier','Delivery')