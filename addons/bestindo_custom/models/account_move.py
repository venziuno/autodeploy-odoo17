# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

class AccountMove(models.Model):
	_inherit = 'account.move'

	name2 = fields.Char('Inv Number')
	is_payment_done = fields.Boolean('Payment Done')
	return_type = fields.Selection([
		('bank','Bank'),
		('cash','Cash'),
		('wallet','Wallet')
	], string='Return Type', default='bank')
	is_credit = fields.Boolean('Credit Invoice')
	total_point = fields.Integer('Point')

	def write(self, vals):
		if vals.get('name2'):
			vals['payment_reference'] = vals.get('name2')
		return super(AccountMove,self).write(vals)

	def action_post(self):
		moves_with_payments = self.filtered('payment_id')
		other_moves = self - moves_with_payments
		if moves_with_payments:
			moves_with_payments.payment_id.action_post()
		if other_moves:
			other_moves._post(soft=False)

		if not self.name2 or self.name == 'Draft':
			if self.move_type == 'out_refund':
				seq_ref = 'bestindo_custom.bp_seq_account_move_return_invoice'
			else:
				seq_ref = 'bestindo_custom.bp_seq_account_move_invoice'

			seq_val = self.env.ref(seq_ref).id
			sequences = self.env['ir.sequence'].browse(seq_val).next_by_id()
			self.name2 = sequences
			self.payment_reference = sequences
		return False
	
	def button_draft(self):
		for move in self:
			if move.payment_state != 'not_paid':
				raise UserError(_("Can't set to draft, Invoice already partial or paid."))
		if any(move.state not in ('cancel', 'posted') for move in self):
			raise UserError(_("Only posted/cancelled journal entries can be reset to draft."))

		exchange_move_ids = set()
		if self:
			self.env['account.full.reconcile'].flush_model(['exchange_move_id'])
			self.env['account.partial.reconcile'].flush_model(['exchange_move_id'])
			self._cr.execute(
				"""
					SELECT DISTINCT sub.exchange_move_id
					FROM (
						SELECT exchange_move_id
						FROM account_full_reconcile
						WHERE exchange_move_id IN %s

						UNION ALL

						SELECT exchange_move_id
						FROM account_partial_reconcile
						WHERE exchange_move_id IN %s
					) AS sub
				""",
				[tuple(self.ids), tuple(self.ids)],
			)
			exchange_move_ids = set([row[0] for row in self._cr.fetchall()])

		for move in self:
			if move.id in exchange_move_ids:
				raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
			if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
				# If the reconciliation was undone, move.tax_cash_basis_rec_id will be empty;
				# but we still don't want to allow setting the caba entry to draft
				# (it'll have been reversed automatically, so no manual intervention is required),
				# so we also check tax_cash_basis_origin_move_id, which stays unchanged
				# (we need both, as tax_cash_basis_origin_move_id did not exist in older versions).
				raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
			if move.restrict_mode_hash_table and move.state == 'posted':
				raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
			# We remove all the analytics entries for this journal
			move.mapped('line_ids.analytic_line_ids').unlink()

		self.mapped('line_ids').remove_move_reconcile()
		self.write({'state': 'draft', 'is_move_sent': False})

class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	def action_register_payment(self):
		''' Open the account.payment.register wizard to pay the selected journal items.
		:return: An action opening the account.payment.register wizard.
		'''
		return {
			'name': _('Make Payment'),
			'res_model': 'account.payment.register',
			'view_mode': 'form',
			'views': [[False, 'form']],
			'context': {
				'active_model': 'account.move.line',
				'active_ids': self.ids,
			},
			'target': 'new',
			'type': 'ir.actions.act_window',
		}

class AccountJournal(models.Model):
	_inherit = 'account.journal'

	@api.onchange('default_account_id')
	def onchange_default_account_id(self):
		if self.default_account_id:
			if self.outbound_payment_method_line_ids:
				self.outbound_payment_method_line_ids.payment_account_id = self.default_account_id.id
			if self.inbound_payment_method_line_ids:
				self.inbound_payment_method_line_ids.payment_account_id = self.default_account_id.id

class AccountPayment(models.Model):
	_inherit = 'account.payment'

	invoice_id = fields.Many2one('account.move','Invoice')