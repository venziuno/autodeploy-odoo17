# -*- coding: utf-8 -*-
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
from datetime import datetime

class AccountPaymentRegister(models.TransientModel):
	_inherit = 'account.payment.register'

	register_line_ids = fields.One2many('account.payment.register.line','register_id','Register Line')

	def action_create_payments(self):
		context = self.env.context
		move = self.env['account.move'].browse(self.env.context.get('active_id'))
		total_paid = sum([x.amount for x in self.register_line_ids])
		if total_paid > (move.amount_residual_signed*-1 if move.amount_residual_signed < 0 else move.amount_residual_signed):
			raise UserError(_(f"Membayar lebih dari Rp {move.amount_residual_signed}."))

		payments = self._create_payments()

		for pay in payments:
			pay.write({'invoice_id':move.id})

		if payments and move.move_type == 'out_invoice':
			sale_id = self.env['sale.order'].search([('name','=',move.invoice_origin)], limit=1)
			if sale_id:
				for pick in sale_id.picking_ids:
					if pick.state in ['assigned']:
						pick.delivery_status = 'ready'
					if pick.state in ['done']:
						sale_id.action_to_done()

			if context.get('bp_deposit_manual') and sale_id.provider_id.is_deposit:
				for reg in self.register_line_ids:
					if reg.journal_id.id == sale_id.provider_id.bp_journal_id.id:
						if sale_id.total_deposit > 0:
							self.env['bp.deposit'].create({
								'name': sale_id.name,
								'partner_id': sale_id.partner_id.id,
								'total': reg.amount*-1,
								'date': sale_id.date_order,
								'user_id': self.env.user.id,
								'state': 'used',
								'sale_id': sale_id.id
							})	

		if payments and move.move_type == 'out_refund':
			sale_id = self.env['sale.order'].search([('name','=',move.invoice_origin)], limit=1)
			if sale_id:
				deposit_id = self.env['bp.deposit'].search([('sale_id','=',sale_id.id),('state','=','used')], limit=1, order='id desc')
				if deposit_id:
					self.env['bp.deposit'].create({
						'name': sale_id.name + ' Return',
						'partner_id': sale_id.partner_id.id,
						'total': total_paid,
						'date': sale_id.date_order,
						'user_id': self.env.user.id,
						'state': 'done',
						'sale_id': sale_id.id
					})

				for line in move.line_ids:
					point_id = self.env['bp.member.point'].search([('sale_id','=',sale_id.id),('product_id','=',line.product_id.id)])
					sale_line_id = self.env['sale.order.line'].search([('order_id','=',sale_id.id),('product_id','=',line.product_id.id)])
					if point_id and sale_line_id:
						point_per_prod = point_id.point/sale_line_id.product_uom_qty
						point_return = point_per_prod*line.quantity
						total_point_return = point_id.point - point_return #450/3 = 150/pcs, return 1 = 450-150 = 300
						if total_point_return > 0:
							point_id.point = total_point_return
						else:
							point_id.unlink()

				if move.total_point:
					point_total_id = self.env['bp.member.point'].search([('sale_id','=',sale_id.id),('product_id','=',False)])
					if point_total_id:
						total_point_now = point_total_id.point
						point_total_id.point = total_point_now + move.total_point

		if self._context.get('dont_redirect_to_payments'):
			return True

		action = {
			'name': _('Payments'),
			'type': 'ir.actions.act_window',
			'res_model': 'account.payment',
			'context': {'create': False},
		}
		if len(payments) == 1:
			action.update({
				'view_mode': 'form',
				'res_id': payments.id,
			})
		else:
			action.update({
				'view_mode': 'tree,form',
				'domain': [('id', 'in', payments.ids)],
			})
		return action

	@api.model
	def default_get(self, fields):
		result = super(AccountPaymentRegister, self).default_get(fields)
		context =  self.env.context
		register_line_ids = []
		move = self.env['account.move'].browse(context['active_id'])
		sale_id = self.env['sale.order'].search([('name','=',move.invoice_origin)], limit=1)
		journal_id = self.env['account.journal'].search([('type','=','bank')], limit=1, order='id asc')
		payment_method_line_id = journal_id.inbound_payment_method_line_ids[0]
		if sale_id.provider_id:
			if sale_id.provider_id.is_deposit:
				if sale_id.total_deposit < move.partner_id.total_deposit:
					journal_id = sale_id.provider_id.bp_journal_id
					if not journal_id:
						raise UserError(_('Please set Journal for Payment Prodiver Deposit.'))
					payment_method_line_id = journal_id.inbound_payment_method_line_ids[0]
				total_deposit = sale_id.total_deposit
				if move.move_type == 'out_refund':
					total_deposit = move.amount_residual_signed*-1 if move.amount_residual_signed < 0 else move.amount_residual_signed
				register_line_ids.append((0, 0, {
					'partner_id': move.partner_id.id,
					'payment_date': datetime.now().strftime('%Y-%m-%d'),
					'journal_id': journal_id.id,
					'communication': move.name,
					'payment_method_line_id': payment_method_line_id.id,
					'amount': total_deposit
				}))
			else:
				if sale_id.provider_id.bp_journal_id:
					journal_id = sale_id.provider_id.bp_journal_id
					payment_method_line_id = journal_id.inbound_payment_method_line_ids[0]
				register_line_ids.append((0, 0, {
					'partner_id': move.partner_id.id,
					'payment_date': datetime.now().strftime('%Y-%m-%d'),
					'journal_id': journal_id.id,
					'communication': move.name,
					'payment_method_line_id': payment_method_line_id.id,
					'amount': move.amount_residual_signed*-1 if move.amount_residual_signed < 0 else move.amount_residual_signed
				}))
		else:
			register_line_ids.append((0, 0, {
				'partner_id': move.partner_id.id,
				'payment_date': datetime.now().strftime('%Y-%m-%d'),
				'journal_id': journal_id.id,
				'communication': move.name,
				'payment_method_line_id': payment_method_line_id.id,
				'amount': move.amount_residual_signed*-1 if move.amount_residual_signed < 0 else move.amount_residual_signed
			}))

		result['register_line_ids'] = register_line_ids
		return result

	def _create_payment_vals_from_wizard(self, batch_result):
		payment_vals_list = []
		for line in self.register_line_ids:
			payment_vals = {
				'date': line.payment_date,
				'amount': line.amount,
				'payment_type': self.payment_type,
				'partner_type': self.partner_type,
				'ref': self.communication,
				'journal_id': line.journal_id.id,
				'company_id': self.company_id.id,
				'currency_id': line.currency_id.id,
				'partner_id': self.partner_id.id,
				'partner_bank_id': self.partner_bank_id.id,
				'payment_method_line_id': line.payment_method_line_id.id,
				'destination_account_id': self.line_ids[0].account_id.id,
				'write_off_line_vals': [],
			}

			if self.payment_difference_handling == 'reconcile':
				if self.early_payment_discount_mode:
					epd_aml_values_list = []
					for aml in batch_result['lines']:
						if aml.move_id._is_eligible_for_early_payment_discount(self.currency_id, line.payment_date):
							epd_aml_values_list.append({
								'aml': aml,
								'amount_currency': -aml.amount_residual_currency,
								'balance': aml.currency_id._convert(-aml.amount_residual_currency, aml.company_currency_id, date=line.payment_date),
							})

					open_amount_currency = self.payment_difference * (-1 if self.payment_type == 'outbound' else 1)
					open_balance = self.currency_id._convert(open_amount_currency, self.company_id.currency_id, self.company_id, line.payment_date)
					early_payment_values = self.env['account.move']._get_invoice_counterpart_amls_for_early_payment_discount(epd_aml_values_list, open_balance)
					for aml_values_list in early_payment_values.values():
						payment_vals['write_off_line_vals'] += aml_values_list

				elif not self.currency_id.is_zero(self.payment_difference):

					if self.writeoff_is_exchange_account:
						# Force the rate when computing the 'balance' only when the payment has a foreign currency.
						# If not, the rate is forced during the reconciliation to put the difference directly on the
						# exchange difference.
						if self.currency_id != self.company_currency_id:
							payment_vals['force_balance'] = sum(batch_result['lines'].mapped('amount_residual'))
					else:
						if self.payment_type == 'inbound':
							# Receive money.
							write_off_amount_currency = self.payment_difference
						else:  # if self.payment_type == 'outbound':
							# Send money.
							write_off_amount_currency = -self.payment_difference

						payment_vals['write_off_line_vals'].append({
							'name': self.writeoff_label,
							'account_id': self.writeoff_account_id.id,
							'partner_id': self.partner_id.id,
							'currency_id': self.currency_id.id,
							'amount_currency': write_off_amount_currency,
							'balance': self.currency_id._convert(write_off_amount_currency, self.company_id.currency_id, self.company_id, line.payment_date),
						})
			payment_vals_list.append(payment_vals)
		return payment_vals_list

	def _create_payment_vals_from_batch(self, batch_result):
		batch_values = self._get_wizard_values_from_batch(batch_result)

		for line in self.register_line_ids:
			if batch_values['payment_type'] == 'inbound':
				partner_bank_id = line.journal_id.bank_account_id.id
			else:
				partner_bank_id = batch_result['payment_values']['partner_bank_id']

			payment_method_line = line.payment_method_line_id

			if batch_values['payment_type'] != payment_method_line.payment_type:
				payment_method_line = line.journal_id._get_available_payment_method_lines(batch_values['payment_type'])[:1]

			payment_vals = {
				'date': line.payment_date,
				'amount': batch_values['source_amount_currency'],
				'payment_type': batch_values['payment_type'],
				'partner_type': batch_values['partner_type'],
				'ref': self._get_batch_communication(batch_result),
				'journal_id': line.journal_id.id,
				'company_id': self.company_id.id,
				'currency_id': batch_values['source_currency_id'],
				'partner_id': batch_values['partner_id'],
				'partner_bank_id': partner_bank_id,
				'payment_method_line_id': payment_method_line.id,
				'destination_account_id': batch_result['lines'][0].account_id.id,
				'write_off_line_vals': [],
			}

			total_amount, mode = self._get_total_amount_using_same_currency(batch_result)
			currency = self.env['res.currency'].browse(batch_values['source_currency_id'])
			if mode == 'early_payment':
				payment_vals['amount'] = total_amount

				epd_aml_values_list = []
				for aml in batch_result['lines']:
					if aml.move_id._is_eligible_for_early_payment_discount(currency, line.payment_date):
						epd_aml_values_list.append({
							'aml': aml,
							'amount_currency': -aml.amount_residual_currency,
							'balance': currency._convert(-aml.amount_residual_currency, aml.company_currency_id, self.company_id, line.payment_date),
						})

				open_amount_currency = (batch_values['source_amount_currency'] - total_amount) * (-1 if batch_values['payment_type'] == 'outbound' else 1)
				open_balance = currency._convert(open_amount_currency, aml.company_currency_id, self.company_id, line.payment_date)
				early_payment_values = self.env['account.move']\
					._get_invoice_counterpart_amls_for_early_payment_discount(epd_aml_values_list, open_balance)
				for aml_values_list in early_payment_values.values():
					payment_vals['write_off_line_vals'] += aml_values_list

		return payment_vals

	def _create_payments(self):
		self.ensure_one()
		all_batches = self._get_batches()
		batches = []
		# Skip batches that are not valid (bank account not trusted but required)
		for batch in all_batches:
			batch_account = self._get_batch_account(batch)
			if self.require_partner_bank_account and not batch_account.allow_out_payment:
				continue
			batches.append(batch)

		if not batches:
			raise UserError(_('To record payments with %s, the recipient bank account must be manually validated. You should go on the partner bank account in order to validate it.', self.payment_method_line_id.name))

		first_batch_result = batches[0]
		edit_mode = self.can_edit_wizard and (len(first_batch_result['lines']) == 1 or self.group_payment)
		to_process = []
		if edit_mode:
			payment_vals_list = self._create_payment_vals_from_wizard(first_batch_result)
			for payment_vals in payment_vals_list:
				to_process_values = {
					'create_vals': payment_vals,
					'to_reconcile': first_batch_result['lines'],
					'batch': first_batch_result,
				}

				# Force the rate during the reconciliation to put the difference directly on the
				# exchange difference.
				if self.writeoff_is_exchange_account and self.currency_id == self.company_currency_id:
					total_batch_residual = sum(first_batch_result['lines'].mapped('amount_residual_currency'))
					to_process_values['rate'] = abs(total_batch_residual / self.amount) if self.amount else 0.0

				to_process.append(to_process_values)
		else:
			# Don't group payments: Create one batch per move.
			if not self.group_payment:
				new_batches = []
				for batch_result in batches:
					for line in batch_result['lines']:
						new_batches.append({
							**batch_result,
							'payment_values': {
								**batch_result['payment_values'],
								'payment_type': 'inbound' if line.balance > 0 else 'outbound'
							},
							'lines': line,
						})
				batches = new_batches

			for batch_result in batches:
				to_process.append({
					'create_vals': self._create_payment_vals_from_batch(batch_result),
					'to_reconcile': batch_result['lines'],
					'batch': batch_result,
				})

		payments = self._init_payments(to_process, edit_mode=edit_mode)
		self._post_payments(to_process, edit_mode=edit_mode)
		self._reconcile_payments(to_process, edit_mode=edit_mode)
		return payments

class AccountPaymentRegisterLine(models.TransientModel):
	_name = 'account.payment.register.line'
	_description = 'Account Payment Register Line'

	name = fields.Char('Name')
	payment_date = fields.Date('Date')
	journal_id = fields.Many2one('account.journal','Journal')
	amount = fields.Monetary('Total')
	currency_id = fields.Many2one('res.currency','Currency', default=lambda self: self.env.company.currency_id.id)
	partner_id = fields.Many2one('res.partner','Partner')
	communication = fields.Char('Memo',related='register_id.communication',store=True)
	payment_method_line_id = fields.Many2one('account.payment.method.line','Payment Method')
	register_id = fields.Many2one('account.payment.register','Register')

	@api.onchange('journal_id')
	def onchange_journal_id(self):
		if self.journal_id:
			payment_method_line_id = self.journal_id.inbound_payment_method_line_ids[0]
			self.payment_method_line_id = payment_method_line_id.id

class AccountMoveReversal(models.TransientModel):
	_inherit = 'account.move.reversal'

	total_point = fields.Integer('Point')
	total_max_point = fields.Integer('Point')
	is_point = fields.Boolean('Is Point')

	@api.model
	def default_get(self, fields):
		res = super(AccountMoveReversal, self).default_get(fields)
		context =  self.env.context
		move = self.env['account.move'].browse(context['active_id'])
		sale_id = self.env['sale.order'].search([('name','=',move.invoice_origin)], limit=1)
		if sale_id:
			if sale_id.total_point:
				res['total_max_point'] = sale_id.total_point
				res['is_point'] = True

		return res

	def reverse_moves(self, is_modify=False):
		self.ensure_one()
		moves = self.move_ids

		if self.total_point > self.total_max_point:
			raise UserError(_(f"Batas Point yang dapat dikembalikan sebesar [{self.total_max_point} Point]."))

		# Create default values.
		default_values_list = []
		for move in moves:
			default_values_list.append(self._prepare_default_reversal(move))

		batches = [
			[self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
			[self.env['account.move'], [], False],  # Others.
		]
		for move, default_vals in zip(moves, default_values_list):
			is_auto_post = default_vals.get('auto_post') != 'no'
			is_cancel_needed = not is_auto_post and (is_modify or self.move_type == 'entry')
			batch_index = 0 if is_cancel_needed else 1
			batches[batch_index][0] |= move
			batches[batch_index][1].append(default_vals)

		# Handle reverse method.
		moves_to_redirect = self.env['account.move']
		for moves, default_values_list, is_cancel_needed in batches:
			new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)
			moves._message_log_batch(
				bodies={move.id: _('This entry has been %s', reverse._get_html_link(title=_("reversed"))) for move, reverse in zip(moves, new_moves)}
			)

			if is_modify:
				moves_vals_list = []
				for move in moves.with_context(include_business_fields=True):
					data = move.copy_data({'date': self.date})[0]
					data['line_ids'] = [line for line in data['line_ids'] if line[2]['display_type'] == 'product']
					moves_vals_list.append(data)
				new_moves = self.env['account.move'].create(moves_vals_list)

			if new_moves:
				line_id = new_moves.line_ids.filtered(lambda p: p.product_id.detailed_type == 'service')
				if line_id:
					line_id.unlink()
				if self.total_point:
					new_moves.total_point = self.total_point
			moves_to_redirect |= new_moves

		self.new_move_ids = moves_to_redirect

		# Create action.
		action = {
			'name': _('Reverse Moves'),
			'type': 'ir.actions.act_window',
			'res_model': 'account.move',
		}
		if len(moves_to_redirect) == 1:
			action.update({
				'view_mode': 'form',
				'res_id': moves_to_redirect.id,
				'context': {'default_move_type':  moves_to_redirect.move_type},
			})
		else:
			action.update({
				'view_mode': 'tree,form',
				'domain': [('id', 'in', moves_to_redirect.ids)],
			})
			if len(set(moves_to_redirect.mapped('move_type'))) == 1:
				action['context'] = {'default_move_type':  moves_to_redirect.mapped('move_type').pop()}
		return action
