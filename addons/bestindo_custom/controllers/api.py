from datetime import datetime, timedelta
from email.headerregistry import Address
from itertools import product
from odoo import http
from odoo.api import Transaction
from odoo.http import request, Response, content_disposition
import json
import odoo
from odoo.exceptions import AccessDenied
import uuid
import base64
from PyPDF2 import PdfFileMerger
import io

class BestindoAPI(http.Controller):
	#All Users ( Driver + Customer + Admin)
	@http.route('/api/login', methods=['POST'], type='http', auth="public", csrf=False, website=True) 
	def api_login(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data
		body = json.loads(body)
		if type(body) == str:
			body = json.loads(body)
		user_obj = env['res.users']
		values = {}
		user = False
		error = {'code': 401, "status": False}
		company = user_obj.browse(uid).company_id

		if body:
			
			username = body.get('username')
			password = body.get('password')

			if not username:
				error['message'] = "Username must be filled"
				error['code'] = 400
			if not password:
				error['message'] = "Password must be filled"
				error['code'] = 400

			try:
				uid = request.session.authenticate(request.db, username, password)
			except:
				uid = False

			if not uid:
				error['message'] = "Wrong username or password"

			if error.get('message'):
				values = error
				return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
			else:
				user = user_obj.sudo().browse(uid)
				partner = user.partner_id
				user.create_token_api()
				if user.share:
					user_type = partner.user_type
				else:
					if partner.user_type == 'driver':
						user_type = partner.user_type
					else:
						user_type = 'admin'
						
				values = {
					'code': 200,
					'status': True,
					'data':{
						'user_id': user.id,
						'user_type': user_type,
						'name': user.name,
						'user_token': user.token_api
					},
					'message': "You are successfully login"
				}
		else:
			error['message'] = "Empty params"
			error['code'] = 400
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})

		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/logout', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_logout(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data
		body = json.loads(body)
		if type(body) == str:
			body = json.loads(body)
		headers = request.httprequest.headers
		error = {'code': 401, 'status': False}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		company = user_obj.browse(uid).company_id

		values = {}

		if headers or post:
			user_id = body.get('user_id')
			user_token = headers.get('Authorization')

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.search([('id','=',int(user_id))],limit = 1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not user_token:
				error['message'] = "User Token must be filled"
				error['code'] = 400
			else: 
				token = user_obj.search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
		else:
			error['message'] = "Headers empty"
			error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			request.session.logout()
			token.token_api = False
			values = {
				'code': 200,
				'status': True,
				'message': "You are successfully logout",
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/reset-password', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_reset_password(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		if type(body) == str:
			body = json.loads(body)

		if body:
			email = body.get('email')
			if not email:
				error['message'] = "Email must be filled"
			else:
				user_id = user_obj.search([('login', '=', email)])
				if not user_id:
					error['message'] = "Email is not registered in the database"
				else:
					user_id.action_reset_password()
					#Jika email gagal, Email di Company wajib di isi


		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			values = {
				'code': 200,
				'status': True,
				'message': "Success, please check your email if you want to reset the password",
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/get-profile', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_profile(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']
		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']

		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			
			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"
     
		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner = user.partner_id
			if partner.user_type == 'customer':
				if partner.image_1920:
					photo = partner.image_1920.decode()
				else:
					photo = ''
				category_ids = env['product.category'].search([('segment_ids','in',partner.segment_ids.ids)])
				address = [
					{'address_type': 'business', 'full_address': partner.full_address},
					{'address_type': 'home', 'full_address': partner.full_address2}
				]
				data = {
					'customer_id': partner.customer_id or '',
					'name': partner.name or '',
					'address': address,
					'phone': partner.phone or '',
					'email': partner.email or '',
					'photo': photo,
					'deposit': partner.total_deposit,
					'point': partner.point_count,
					'is_negotiation': partner.is_negotiation,
					'segment_ids': partner.segment_ids.ids,
					'category_ids': category_ids.ids,
					'provider_ids': partner.payment_provider_ids.ids
				}
			else:
				if partner.image_1920:
					photo = partner.image_1920.decode()
				else:
					photo = ''

				data = {
					'driver_id': partner.customer_id or '',
					'name': partner.name or '',
					'driver_address': partner.full_address or '',
					'phone': partner.phone or '',
					'email': partner.email or '',
					'photo': photo,
					'driver_info': {
						'id_confirmation': partner.driver_id_no or '',
						'driver_license': partner.driver_sim or '',
						'merk': partner.driver_merk or '',
						'type': partner.driver_type or '',
						'plat': partner.driver_no or '',
						'color': partner.driver_color or ''
					}
				}
			
			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/update-profile', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_update_profile(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		company = user_obj.browse(uid).company_id
		
		if body or headers:
			user_token = headers.get('Authorization')
			photo = body.get('photo')
			name = body.get('name')
			email = body.get('email')
			phone = body.get('phone')
			user_id = body.get('user_id')
			update_profile = {}

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not photo:
				error['message'] = "Photo must be filled"
				error['code'] = 400
			else:
				update_profile['image_1920'] = photo.encode()
			if name:
				update_profile['name'] = name
			if email:
				update_profile['email'] = email
			if phone:
				update_profile['phone'] = phone

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner = user.partner_id
			if partner:
				partner.write(update_profile)

			values = {
				'code': 200,
				'status': True,
				'message': "You are successfully Update Profile"
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	#Customer
	
	@http.route('/api/promotion', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_promotion(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		bp_promotion_obj = env['bp.promotion']
		company = user_obj.browse(uid).company_id
		
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')

			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"
				
		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			datas = bp_promotion_obj.search([])
			data = []
			
			for promotion in datas:
				state = promotion.state
				if state == "open":
					if promotion.is_all_product:
						products = env['product.product'].search([('detailed_type', '!=', 'service')])
						image = ''
						if promotion.image:
							image = promotion.image.decode()
						data.append({
							"id": promotion.id,
							"name": promotion.name or '',
							"image": image or '',
							"disc_type" : promotion.disc_type or '',
							"disc_flat" : promotion.disc_flat or 0,
							"disc_percent" : promotion.disc_percent or 0,
							"is_all_product" : promotion.is_all_product,
							"state" : promotion.state or '',
							"product_ids" : [product.id for product in products] or [],
							"start_date" : promotion.start_date.strftime('%Y-%m-%d %H:%M:%S') if promotion.start_date else '',
							"end_date" : promotion.end_date.strftime('%Y-%m-%d %H:%M:%S') if promotion.end_date else '',
							"description": promotion.description or ''
						})
					else :
						image = ''
						if promotion.image:
							image = promotion.image.decode()
						data.append({
							"id": promotion.id,
							"name": promotion.name or '',
							"image": image or '',
							'discount_type': promotion.disc_type or '',
							'discount_flat': promotion.disc_flat if promotion.disc_type == 'flat' else 0,
							'discount_percent': promotion.disc_percent if promotion.disc_type == 'percent' else 0,
							"is_all_product" : promotion.is_all_product,
							"state" : promotion.state or '',
							"product_ids" : [x.product_id.id for x in promotion.line_ids] or [],
							"start_date" : promotion.start_date.strftime('%Y-%m-%d %H:%M:%S') if promotion.start_date else '',
							"end_date" : promotion.end_date.strftime('%Y-%m-%d %H:%M:%S') if promotion.end_date else '',
							"description": promotion.description or ''
						})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/promotion_detail', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_promotion_detail(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		headers = request.httprequest.headers

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		bp_promotion_obj = env['bp.promotion']
		company = user_obj.browse(uid).company_id
		
		if headers or post:
			user_token = headers.get('Authorization')
			promotion_id = post.get('promotion_id')

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

			if not promotion_id:
				error['message'] = "Promotion ID must be filled"
				error['code'] = 400
			else:
				promotion = bp_promotion_obj.sudo().search([('id','=',int(promotion_id))], limit=1)
				if not promotion:
					error['message'] = "Promotion ID is not registered in the database"
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner = user.partner_id
			state = promotion.state
			products = []
			if state == "open":
				if promotion.is_all_product:
					product_ids = env['product.product'].sudo().search([('detailed_type', '!=', 'service')])
					for product in product_ids:
						photo = product.image_1920.decode() if product.image_1920 else ''
						
						variant_name = ''
						if product.product_template_variant_value_ids:
							variant_name = ' - '.join(x.name for x in product.product_template_variant_value_ids)
						
						updated_price = ''
						if product.last_price:
							if product.list_price < product.last_price:
								updated_price = 'down'
							if product.list_price > product.last_price:
								updated_price = 'up'

						fav_product_id = env['bp.favorite.product'].search([('partner_id','=',partner.id),('product_id','=',product.id)], limit=1)
						is_favorite = False
						if fav_product_id:
							is_favorite = True

						products.append({
							'product_id': product.id,
							'name': product.name,
							'variant_name': variant_name,
							'price_unit': product.list_price,
							'updated_price': updated_price,
							'point_type': product.point_type or '',
							'point': product.percent_point,
							'image': photo,
							'total_sold': product.sales_count,
							'category': {
								'id': product.categ_id.id,
								'name': product.categ_id.name
								},
							'segment': [{'id':x.id,'name': x.name} for x in product.segment_ids] or [],
							'is_favorite': is_favorite,
							'description': product.description or ''
						})
				else:
					for pro in promotion.line_ids:
						product = pro.product_id
						photo = product.image_1920.decode() if product.image_1920 else ''
						
						variant_name = ''
						if product.product_template_variant_value_ids:
							variant_name = ' - '.join(x.name for x in product.product_template_variant_value_ids)
						
						updated_price = ''
						if product.last_price:
							if product.list_price < product.last_price:
								updated_price = 'down'
							if product.list_price > product.last_price:
								updated_price = 'up'

						fav_product_id = env['bp.favorite.product'].search([('partner_id','=',partner.id),('product_id','=',product.id)], limit=1)
						is_favorite = False
						if fav_product_id:
							is_favorite = True

						products.append({
							'product_id': product.id,
							'name': product.name,
							'variant_name': variant_name,
							'price_unit': product.list_price,
							'updated_price': updated_price,
							'point_type': product.point_type or '',
							'point': product.percent_point,
							'image': photo,
							'total_sold': product.sales_count,
							'category': {
								'id': product.categ_id.id,
								'name': product.categ_id.name
								},
							'segment': [{'id':x.id,'name': x.name} for x in product.segment_ids] or [],
							'is_favorite': is_favorite,
							'description': product.description or ''
						})

			image = ''
			if promotion.image:
				image = promotion.image.decode()
			data = {
				"id": promotion.id,
				"name": promotion.name or '',
				"image": image or '',
				'discount_type': promotion.disc_type or '',
				'discount_flat': promotion.disc_flat if promotion.disc_type == 'flat' else 0,
				'discount_percent': promotion.disc_percent if promotion.disc_type == 'percent' else 0,
				"is_all_product" : promotion.is_all_product,
				"state" : promotion.state or '',
				"products" : products,
				"start_date" : promotion.start_date.strftime('%Y-%m-%d %H:%M:%S') if promotion.start_date else '',
				"end_date" : promotion.end_date.strftime('%Y-%m-%d %H:%M:%S') if promotion.end_date else '',
				"description": promotion.description or ''
			}

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/discount_product', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_discount_product(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		headers = request.httprequest.headers

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		bp_promotion_obj = env['bp.promotion']
		bp_promotion_line_obj = env['bp.promotion.line']

		company = user_obj.browse(uid).company_id
		
		if headers or post:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			data = []
			partner = user.partner_id
			line_ids = bp_promotion_line_obj.search([('promotion_id','!=',False),('promotion_id.state','=','open')])
			promotion_ids = bp_promotion_obj.search([('is_all_product','=',True),('state','=','open')], limit=1, order='id desc')
			for line in line_ids:
				product = line.product_id
				promotion_id = line.promotion_id
				photo = product.image_1920.decode() if product.image_1920 else ''
						
				variant_name = ''
				if product.product_template_variant_value_ids:
					variant_name = ' - '.join(x.name for x in product.product_template_variant_value_ids)
				
				updated_price = ''
				if product.last_price:
					if product.list_price < product.last_price:
						updated_price = 'down'
					if product.list_price > product.last_price:
						updated_price = 'up'

				fav_product_id = env['bp.favorite.product'].search([('partner_id','=',partner.id),('product_id','=',product.id)], limit=1)
				is_favorite = False
				if fav_product_id:
					is_favorite = True

				data.append({
					'promotion_id': promotion_id.id,
					'promotion_name': promotion_id.name,
					'discount_type': promotion_id.disc_type or '',
					'discount_flat': promotion_id.disc_flat if promotion_id.disc_type == 'flat' else 0,
					'discount_percent': promotion_id.disc_percent if promotion_id.disc_type == 'percent' else 0,
					'product_id': product.id,
					'name': product.name,
					'variant_name': variant_name,
					'price_unit': product.list_price,
					'updated_price': updated_price,
					'image': photo,
					'total_sold': product.sales_count,
					'category': {
						'id': product.categ_id.id,
						'name': product.categ_id.name
						},
					'segment': [{'id':x.id,'name': x.name} for x in product.segment_ids] or [],
					'is_favorite': is_favorite,
					'description': product.description or ''
				})

			if promotion_ids:
				product_ids = env['product.product'].sudo().search([('detailed_type', '!=', 'service')])
				for product in product_ids:
					promotion_line = bp_promotion_line_obj.search([('promotion_id','!=',False),('promotion_id.state','=','open'),('product_id','=',product.id)])
					if promotion_line:
						continue

					photo = product.image_1920.decode() if product.image_1920 else ''
					
					variant_name = ''
					if product.product_template_variant_value_ids:
						variant_name = ' - '.join(x.name for x in product.product_template_variant_value_ids)
					
					updated_price = ''
					if product.last_price:
						if product.list_price < product.last_price:
							updated_price = 'down'
						if product.list_price > product.last_price:
							updated_price = 'up'

					fav_product_id = env['bp.favorite.product'].search([('partner_id','=',partner.id),('product_id','=',product.id)], limit=1)
					is_favorite = False
					if fav_product_id:
						is_favorite = True

					data.append({
						'promotion_id': promotion_ids.id,
						'promotion_name': promotion_ids.name,
						'discount_type': promotion_ids.disc_type or '',
						'discount_flat': promotion_ids.disc_flat if promotion_ids.disc_type == 'flat' else 0,
						'discount_percent': promotion_ids.disc_percent if promotion_ids.disc_type == 'percent' else 0,
						'product_id': product.id,
						'name': product.name,
						'variant_name': variant_name,
						'price_unit': product.list_price,
						'updated_price': updated_price,
						'point_type': product.point_type or '',
						'point': product.percent_point,
						'image': photo,
						'total_sold': product.sales_count,
						'category': {
							'id': product.categ_id.id,
							'name': product.categ_id.name
							},
						'segment': [{'id':x.id,'name': x.name} for x in product.segment_ids] or [],
						'is_favorite': is_favorite,
						'description': product.description or ''
					})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'total_data': len(data),
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/best_seller_product', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_best_seller_product(self, **post):
		cr, uid, pool, context = request.cr, request.env.uid, request.registry, request.context
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users'].sudo()
		partner_obj = env['res.partner']
		
		company = user_obj.browse(uid).company_id
		
		# if isinstance(body, str):
		# 	body = json.loads(body)

		error = {'code': 401, 'status': False}
		values = {}
		data = []

		# user_id = post.get('user_id')
		user_token = headers.get('Authorization')

		# if not user_id:
		# 	error['message'] = "User ID must be filled"
		# else:
		# 	user = user_obj.search([('id','=',int(user_id))], limit=1)
		# 	if not user:
		# 		error['message'] = "User ID is not registered in the database"

		# if not user_token:
		# 	error['message'] = "Token must be filled"
		# else:
		# 	token = user_obj.search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
		# 	if not token:
		# 		error['message'] = "Invalid user_token"

		if not user_token:
			error['message'] = "Token must be filled"
			error['code'] = 400
		else:
			user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
			if not user:
				error['message'] = "Invalid user_token"

		if 'message' in error:
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner = user.partner_id
			segment_ids = partner.segment_ids.ids
			product_ids = env['product.product'].sudo().search([
				('detailed_type', '!=', 'service'),
				('segment_ids', 'in', segment_ids),
			])
			
			product_list = [product for product in product_ids]
			sorted_products = sorted(product_list, key=lambda p: p.sales_count, reverse=True)

			top_products = sorted_products[:5]
			for product in top_products:
				photo = product.image_1920.decode() if product.image_1920 else ''
				variant_name = ' - '.join(x.name for x in product.product_template_variant_value_ids)
				data.append({
					'total_sold': product.sales_count,
					'id': product.id,
					'name': product.name or '',
					'variant_name': variant_name or '',
					'price': product.list_price,
					'point_type': product.point_type or '',
					'point': product.percent_point,
					'segment_ids': product.segment_ids.ids or [],
					'image': photo,
				})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/product_segment', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_product_segment(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = []
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		product_segment_obj = env['product.segment']

		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			segment_ids = post.get('segment_ids')

			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"
			
			if not segment_ids:
				error['message'] = "Segment IDs must be filled"
				error['code'] = 400
			else:
				segment_ids = json.loads(segment_ids)
				if type(segment_ids) != list:
					error['message'] = "Segment IDs must type List [id1,id2,..]"
					error['code'] = 400

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			datas = product_segment_obj.search([('id','in',segment_ids)])
			data = []
			
			for segment in datas:
				image = segment.icon_img.decode() if segment.icon_img else ''
				data.append({
					"id": segment.id,
					"name": segment.name or '',
					"image": image
				})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/product_category', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_product_category(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = []
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		product_categ_obj = env['product.category']

		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			segment_ids = post.get('segment_ids')

			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

			if not segment_ids:
				error['message'] = "Segment IDs must be filled"
				error['code'] = 400
			else:
				segment_ids = json.loads(segment_ids)
				if type(segment_ids) != list:
					error['message'] = "Segment IDs must type List [id1,id2,..]"
					error['code'] = 400

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			if segment_ids:
				datas = product_categ_obj.search([('segment_ids','in',segment_ids)])
			else:
				datas = product_categ_obj.search([])

			data = []
			
			for categ in datas:
				image = categ.icon_img.decode() if categ.icon_img else ''
				data.append({
					"id": categ.id,
					"name": categ.name or '',
					"image": image
				})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/product', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_product(self, **post):
		cr, uid, pool, context = request.cr, request.env.uid, request.registry, request.context
		env = request.env
		headers = request.httprequest.headers
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		bp_promotion_obj = env['bp.promotion']
		bp_promotion_line_obj = env['bp.promotion.line']
		company = user_obj.browse(uid).company_id
		
		error = {'code': 401, 'status': False}
		values = {}
		data = []

		name = post.get('search','')
		user_token = headers.get('Authorization')
		page = int(post.get('page', 1))
		limit = int(post.get('limit', 5))
		offset = (page - 1) * limit
		segment_ids = post.get('segment_ids',[])
		category_ids = post.get('category_ids',[])
		min_price = post.get('min_price')
		max_price = post.get('max_price')
		updated = post.get('updated')
		sort = post.get('sort')
		discount_product = post.get('discount_product',0)

		if not user_token:
			error['message'] = "Token must be filled"
			error['code'] = 400
		else:
			user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
			if not user:
				error['message'] = "Invalid user_token"

		if not segment_ids:
			error['message'] = "Segment IDs must be filled"
			error['code'] = 400
		else:
			segment_ids = json.loads(segment_ids)
			if type(segment_ids) != list:
				error['message'] = "Segment IDs must type List [id1,id2,..]"
				error['code'] = 400

		if category_ids:
			category_ids = json.loads(category_ids)
			if type(category_ids) != list:
				error['message'] = "Category IDs must type List [id1,id2,..]"
				error['code'] = 400

		if sort:
			if sort not in ['asc','desc']:
				error['message'] = 'Wrong value for sort, please use asc or desc'
				error['code'] = 400

		if updated:
			try:
				updated = json.loads(updated)
				if updated not in [0,1]:
					error['message'] = 'Wrong value for updated, please 0 or 1'
					error['code'] = 400
			except:
				error['message'] = 'Wrong value for updated, please 0 or 1'
				error['code'] = 400

		if discount_product:
			try:
				discount_product = json.loads(discount_product)
				if discount_product not in [0,1]:
					error['message'] = 'Wrong value for discount_product, please 0 or 1'
					error['code'] = 400
			except:
				error['message'] = 'Wrong value for discount_product, please 0 or 1'
				error['code'] = 400

		if 'message' in error:
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner = user.partner_id
			# segment_ids = partner.segment_ids.ids
			domain_search = [
				('detailed_type', '!=', 'service'),
				('segment_ids', 'in', segment_ids)
			]
			if name:
				domain_search += [('name','ilike',name)]
			if category_ids and type(category_ids) == list:
				domain_search += [('categ_id','in',category_ids)]
			if min_price and not max_price:
				domain_search += [('list_price','>=',min_price)]
			if not min_price and max_price:
				domain_search += [('list_price','<=',max_price)]
			if min_price and max_price:
				domain_search += [('list_price','>=',min_price),('list_price','<=',max_price)]

			if (updated in [0,1]) and sort:
				product_ids = env['product.product'].sudo().search(domain_search, limit=limit, offset=offset, order=f"name {sort}, write_date {'desc' if updated == 1 else 'asc' }")
			elif (updated in [0,1]) and not sort:
				product_ids = env['product.product'].sudo().search(domain_search, limit=limit, offset=offset, order=f"write_date {'desc' if updated == 1 else 'asc' }")
			elif (updated not in [0,1]) and sort:
				product_ids = env['product.product'].sudo().search(domain_search, limit=limit, offset=offset, order=f"name {sort}")
			else:
				product_ids = env['product.product'].sudo().search(domain_search, limit=limit, offset=offset)
			for product in product_ids:
				discount_data = {}
				photo = product.image_1920.decode() if product.image_1920 else ''
				variant_name = ''
				if product.product_template_variant_value_ids:
					variant_name = ' - '.join(x.name for x in product.product_template_variant_value_ids)
				updated_price = ''
				if product.last_price:
					if product.list_price < product.last_price:
						updated_price = 'down'
					if product.list_price > product.last_price:
						updated_price = 'up'

				is_discount = False
				promotion_id = bp_promotion_obj.search([('is_all_product','=',True),('state','=','open')], limit=1, order='id desc')
				if promotion_id:
					value = 0
					discount_price = 0
					if promotion_id.disc_type == 'percent':
						value = promotion_id.disc_percent
						discount_price = product.list_price*(1-value)
					if promotion_id.disc_type == 'flat':
						value = promotion_id.disc_flat
						discount_price = product.list_price - value
					discount_data.update({
						'promotion_id': promotion_id.id,
						'promotion_name': promotion_id.name,
						'type': promotion_id.disc_type or '',
						'value': value*100 if value < 1 else value,
						'discount_price': discount_price if discount_price > 0 else 0
					})
					is_discount = True
				else:
					promotion_line_id = bp_promotion_line_obj.search([('product_id','=',product.id),('promotion_id','!=',False),('promotion_id.state','=','open')])
					if promotion_line_id:
						promotion_id = promotion_line_id.promotion_id
						value = 0
						discount_price = 0
						if promotion_id.disc_type == 'percent':
							value = promotion_id.disc_percent
							discount_price = product.list_price*(1-value)
						if promotion_id.disc_type == 'flat':
							value = promotion_id.disc_flat
							discount_price = product.list_price - value
						discount_data.update({
							'promotion_id': promotion_id.id,
							'promotion_name': promotion_id.name,
							'type': promotion_id.disc_type or '',
							'value': value*100 if value < 1 else value,
							'discount_price': discount_price if discount_price > 0 else 0
						})
						is_discount = True

				if discount_product == 1:
					if not is_discount:
						continue

				data.append({
					'id': product.id,
					'name': product.name or '',
					'variant_name': variant_name or '',
					'price': product.list_price,
					'updated_price': updated_price,
					'point_type': product.point_type or '',
					'point': product.percent_point,
					'image': photo,
					'total_sold': int(product.sales_count),
					'category': {
						'id': product.categ_id.id,
						'name': product.categ_id.name
					},
					'segment': [{'id':x.id,'name': x.name} for x in product.segment_ids] or [],
					'is_discount': is_discount,
					'discount': discount_data,
					"description": product.description or ''
				})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'pagination': {
					'page': page,
					'limit': limit,
					'total_items': len(data) if discount_product == 1 else len(product_ids)
				},
				'message': 'Success'
			}
		
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/product_detail', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_product_detail(self, **post):
		cr, uid, pool, context = request.cr, request.env.uid, request.registry, request.context
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		product_obj = env['product.product']
		bp_promotion_obj = env['bp.promotion']
		bp_promotion_line_obj = env['bp.promotion.line']
				
		# if isinstance(body, str):
		# 	body = json.loads(body)

		error = {'code': 401, 'status': False}
		values = {}
		data = []

		# user_id = post.get('user_id')
		product_id = post.get('product_id')
		user_token = headers.get('Authorization')

		# if not user_token:
		# 	error['message'] = "Token must be filled"
		# else:
		# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
		# 	if not token:
		# 		error['message'] = "Invalid user_token"

		# if not user_id:
		# 	error['message'] = "User ID must be filled"
		# else:
		# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
		# 	if not user:
		# 		error['message'] = "User ID is not registered in the database"

		if not user_token:
			error['message'] = "Token must be filled"
			error['code'] = 400
		else:
			user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
			if not user:
				error['message'] = "Invalid user_token"

		if not product_id:
			error['message'] = "Product ID must be filled"
			error['code'] = 400
		else:
			product_ids = product_obj.sudo().search([('id','=',int(product_id))])
			if not product_ids:
				error['message'] = "Product ID is not registered in the database"
				error['code'] = 400					

		if 'message' in error:
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner = user.partner_id
			
			for product in product_ids:
				discount_data = {}
				value = 0
				discount_price = 0
				photo = product.image_1920.decode() if product.image_1920 else ''
				variant_name = ''
				if product.product_template_variant_value_ids:
					variant_name = ' - '.join(x.name for x in product.product_template_variant_value_ids)
				updated_price = ''
				if product.last_price:
					if product.list_price < product.last_price:
						updated_price = 'down'
					if product.list_price > product.last_price:
						updated_price = 'up'

				fav_product_id = env['bp.favorite.product'].search([('partner_id','=',partner.id),('product_id','=',product.id)], limit=1)
				is_favorite = False
				if fav_product_id:
					is_favorite = True

				is_discount = False
				promotion_id = bp_promotion_obj.search([('is_all_product','=',True),('state','=','open')], limit=1, order='id desc')
				if promotion_id:
					if promotion_id.disc_type == 'percent':
						value = promotion_id.disc_percent
						discount_price = product.list_price*(1-value)
					if promotion_id.disc_type == 'flat':
						value = promotion_id.disc_flat
						discount_price = product.list_price - value
					discount_data.update({
						'promotion_id': promotion_id.id,
						'promotion_name': promotion_id.name,
						'type': promotion_id.disc_type or '',
						'value': value*100 if value < 1 else value,
						'discount_price': discount_price if discount_price > 0 else 0 
					})
					is_discount = True
				else:
					promotion_line_id = bp_promotion_line_obj.search([('product_id','=',product.id),('promotion_id','!=',False),('promotion_id.state','=','open')])
					if promotion_line_id:
						promotion_id = promotion_line_id.promotion_id
						if promotion_id.disc_type == 'percent':
							value = promotion_id.disc_percent
							discount_price = product.list_price*(1-value)
						if promotion_id.disc_type == 'flat':
							value = promotion_id.disc_flat
							discount_price = product.list_price - value
						discount_data.update({
							'promotion_id': promotion_id.id,
							'promotion_name': promotion_id.name,
							'type': promotion_id.disc_type or '',
							'value': value*100 if value < 1 else value,
							'discount_price': discount_price if discount_price > 0 else 0
						})
						is_discount = True

				data = {
					'id': product.id,
					'name': product.name or '',
					'variant_name': variant_name or '',
					'price': product.list_price,
					'updated_price': updated_price,
					'point_type': product.point_type or '',
					'point': product.percent_point,
					'image': photo,
					'total_sold': product.sales_count,
					'category': {
						'id': product.categ_id.id,
						'name': product.categ_id.name
					},
					'segment': [{'id':x.id,'name': x.name} for x in product.segment_ids] or [],
					'is_discount': is_discount,
					'discount': discount_data,
					'is_favorite': is_favorite,
					"description": product.description or ''
				}

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/get_favorite_product', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_favorite_product(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']
		page = int(post.get('page', 1))
		limit = int(post.get('limit', 10))
		offset = (page - 1) * limit
		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		favorite_product_obj = env['bp.favorite.product']
		
		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"

			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner_id = user.partner_id
			total_products = favorite_product_obj.search_count([('partner_id', '=', partner_id.id)])
			datas = favorite_product_obj.search([('partner_id', '=', partner_id.id)], limit=limit, offset=offset)
			data = []
			
			for favorite_product in datas:
				if favorite_product.image:
					photo = favorite_product.image.decode()
				else:
					photo = ''

				variant_name = ''
				if favorite_product.product_id.product_template_variant_value_ids:
					variant_name = ' - '.join(x.name for x in favorite_product.product_id.product_template_variant_value_ids)

				updated_price = ''
				if favorite_product.product_id.last_price:
					if favorite_product.product_id.list_price < favorite_product.product_id.last_price:
						updated_price = 'down'
					if favorite_product.product_id.list_price > favorite_product.product_id.last_price:
						updated_price = 'up'

				data.append({
					"id": favorite_product.id,
					"product_id": favorite_product.product_id.id,
					"name": favorite_product.product_id.name or '',
					"variant_name": variant_name,
					"price": favorite_product.product_id.list_price,
					"updated_price": updated_price,
					"point_type": favorite_product.product_id.point_type or '',
					"point": favorite_product.product_id.percent_point,
					"image": photo,
					"total_sold": favorite_product.product_id.sales_count,
					"category": {
						"id": favorite_product.product_id.categ_id.id,
						"name": favorite_product.product_id.categ_id.name
					},
					"segment": [{"id":x.id,"name": x.name} for x in favorite_product.product_id.segment_ids] or [],
					"description": favorite_product.product_id.description or ''
				})
				
			values = {
			'code': 200,
			'status': True,
			'data': data,
			'message': 'Success',
			'pagination': {
					'current_page': page,
					'limit': limit,
					'total_products': total_products,
					'total_pages': (total_products + limit - 1) // limit,  # Calculate total pages
				}
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/add_favorite_product', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_add_favorite_product(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		user_obj = env['res.users']
		
		company = user_obj.browse(uid).company_id
		if type(body) == str:
			body = json.loads(body)
		
		if body or headers:
			user_id = body.get('user_id')
			product_id = body.get('product_id')
			user_token = headers.get('Authorization')
			
			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400
			if not product_id:
				error['message'] = "Product must be filled"
				error['code'] = 400
			else: 
				product_id = env['product.product'].sudo().search([('id','=',int(product_id))])
				if not product_id:
					error['message'] = "Product is not registered in the database"
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			favorite_product_id = env['bp.favorite.product'].search([('product_id','=',product_id.id),('partner_id','=',user.partner_id.id)], limit=1)
			if not favorite_product_id:
				favorite_product_id = env['bp.favorite.product'].create({
					'product_id': product_id.id,
					'partner_id': user.partner_id.id
				})

			values = {
				'code': 200,
				'status': True,
				'data':{
					'favorite_product_id' : favorite_product_id.id
				}, 
				'message': 'Product successfully added to favorites list'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/delete_favorite_product', methods=['DELETE'], type='http', auth="public", csrf=False, website=True)
	def api_delete_favorite_product(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		user_obj = env['res.users']
		
		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			product_id = post.get('product_id')

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user_id = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user_id:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400
			
			if not product_id:
				error['message'] = "Product must be filled"
				error['code'] = 400
			else: 
				product_id = env['product.product'].sudo().search([('id','=',int(product_id))])
				if not product_id:
					error['message'] = "Product is not registered in the database"
					error['code'] = 400
			
			if user_id and product_id:
				partner_id = user_id.partner_id
				favorite_product_id = env['bp.favorite.product'].search([('product_id','=',product_id.id),('partner_id','=',partner_id.id)])
				if not favorite_product_id:
					error['message'] = "Product Favorite not found for this product"
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
    
		else:
			favorite_product_id.unlink()

			values = {
				'code': 200,
				'status': True,
				'message': 'Product successfully deleted to favorites list'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/get_cart', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_cart(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		sale_obj = env['sale.order']

		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')

			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"
			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"
				
		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner_id = user.partner_id
			cart_line = []
			cart_ids = env['bp.cart'].search([('partner_id','=',partner_id.id),('state','in',[False, 'draft'])], order='id desc')

			for cart in cart_ids:
				is_discount = False
				disc_type = ''
				value = 0
				discount_price = 0
				discount_data = {}
				variant_name = ''
				if cart.product_id.product_template_variant_value_ids:
					variant_name = ' - '.join(x.name for x in cart.product_id.product_template_variant_value_ids)

				photo = cart.product_id.image_1920.decode() if cart.product_id.image_1920 else ''

				if cart.disc_flat or cart.disc_percent:
					is_discount = True
					if cart.disc_percent > 0:
						disc_type = 'percent'
						value = cart.disc_percent
						discount_price = cart.product_id.list_price*(1-cart.disc_percent)
					if cart.disc_flat > 0:
						disc_type = 'flat'
						value = cart.disc_flat
						discount_price = cart.product_id.list_price - cart.disc_flat
				
				if is_discount:
					discount_data.update({
						'type': disc_type,
						'value': value*100 if value < 1 else value,
						'discount_price': discount_price if discount_price > 0 else 0,
						'total_discounted': cart.product_uom_qty*discount_price
					})

				cart_line.append({
					'cart_id': cart.id,
					'product_id': cart.product_id.id,
					'name': cart.product_id.name,
					'price': cart.product_id.list_price,
					'variant_name': variant_name,
					'product_uom_qty': cart.product_uom_qty,
					'is_discount': is_discount,
					'discount': discount_data,
					'image': photo
				})

			values = {
				'code': 200,
				'status': True,
				'data': cart_line,
				'total_cart': len(cart_line),
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/add_cart', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_add_cart(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		
		company = user_obj.browse(uid).company_id
		if type(body) == str:
			body = json.loads(body)
		
		if body or headers:
			user_id = body.get('user_id')
			user_token = headers.get('Authorization')
			product_id = body.get('product_id')
			product_uom_qty = body.get('product_uom_qty')

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400
			
			if not product_id:
				error['message'] = "Product must be filled"
				error['code'] = 400
			else: 
				product_id = env['product.product'].sudo().search([('id','=',int(product_id))])
				if not product_id:
					error['message'] = "Product is not registered in the database"
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})

		else:
			partner_id = user.partner_id
			disc_percent = 0
			disc_flat = 0
			cart_id = env['bp.cart'].search([('partner_id','=', partner_id.id),('product_id','=',product_id.id),('state','in',[False, 'draft'])])
			promotion_line_id = env['bp.promotion.line'].search([('product_id','=',product_id.id),('promotion_id','!=',False),('promotion_id.state','=','open')], limit=1, order='id desc')
			if promotion_line_id:
				promotion_id = promotion_line_id.promotion_id
				if promotion_id.start_date and promotion_id.end_date:
					if (datetime.now() > promotion_id.start_date and datetime.now() < promotion_id.end_date) and promotion_id.state == 'open':
						if promotion_id.disc_type == 'flat':
							disc_flat = promotion_id.disc_flat
						if promotion_id.disc_type == 'percent':
							disc_percent = promotion_id.disc_percent
				else:
					if promotion_id.disc_type == 'flat':
						disc_flat = promotion_id.disc_flat
					if promotion_id.disc_type == 'percent':
						disc_percent = promotion_id.disc_percent

			promotion_all_prod_id = env['bp.promotion'].search([('is_all_product','=',True),('state','=','open')], limit=1, order='id desc')
			if promotion_all_prod_id:
				if promotion_all_prod_id.start_date and promotion_all_prod_id.end_date:
					if (datetime.now() > promotion_all_prod_id.start_date and datetime.now() < promotion_all_prod_id.end_date):
						if promotion_all_prod_id.disc_type == 'flat':
							disc_flat = promotion_all_prod_id.disc_flat
						if promotion_all_prod_id.disc_type == 'percent':
							disc_percent = promotion_all_prod_id.disc_percent
				else:
					if promotion_all_prod_id.disc_type == 'flat':
						disc_flat = promotion_all_prod_id.disc_flat
					if promotion_all_prod_id.disc_type == 'percent':
						disc_percent = promotion_all_prod_id.disc_percent

			if cart_id:
				up_quantity = product_uom_qty or (cart_id.product_uom_qty + 1)
				cart_write = {
					'product_uom_qty': up_quantity,
					'disc_percent': disc_percent,
					'disc_flat': disc_flat
				}
				cart_id.write(cart_write)
			else: 
				cart_id = env['bp.cart'].create({
					'name': product_id.name,
					'partner_id': partner_id.id,
					'product_id': product_id.id,
					'product_uom_qty': product_uom_qty or 1,
					'disc_percent': disc_percent,
					'disc_flat': disc_flat
				})
			
			values = {
				'code': 200,
				'status': True,
				'data': {
					'cart_id': cart_id.id
				},
				'message': 'Product successfully add to cart'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/delete_cart', methods=['DELETE'], type='http', auth="public", csrf=False, website=True)
	def api_delete_cart(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		user_obj = env['res.users']
		
		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			cart_id = post.get('cart_id')
			
			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not cart_id:
				error['message'] = "Cart ID must be filled"
				error['code'] = 400
			else:
				cart = env['bp.cart'].search([('id','=',int(cart_id))], limit=1)
				if not cart:
					error['message'] = "Cart ID is not registered in the database"
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})

		else:
			partner_id = user.partner_id
			
			if cart:
				cart.unlink()

			values = {
				'code': 200,
				'status': True,
				'message': 'Product successfully deleted from cart'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/create_transaction', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_create_transaction(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		sale_obj = env['sale.order']

		company = user_obj.browse(uid).company_id
		if type(body) == str:
			body = json.loads(body)
		
		if body or headers:
			user_token = headers.get('Authorization')
			user_id = body.get('user_id')
			cart_ids = body.get('cart_ids',[])

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not cart_ids:
				error['message'] = "Cart IDs must be filled"
				error['code'] = 400
			else:
				if type(cart_ids) != list:
					error['message'] = "Cart IDs must type List [id1,id2,..]"
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner_id = user.partner_id
			cart_line = []
			cart_ids = env['bp.cart'].browse(cart_ids)
			ordered_cart_ids = env['bp.cart'].search([('partner_id','=',partner_id.id),('order_id','!=',False),('state','=','draft')])
			ordered_cart_ids.write({'order_id': False})

			for cart in cart_ids:
				cart_line.append(
					(0, 0, {'name': cart.product_id.name,
							'product_id': cart.product_id.id, 
							'product_uom_qty': cart.product_uom_qty,
							'disc_percent': cart.disc_percent,
							'disc_flat': cart.disc_flat})
				)

			sale_id = env['sale.order'].search([('partner_id','=',partner_id.id),('state','=','draft')], limit=1, order='id desc')
			delivery_id = env['delivery.carrier'].search([('is_cod','=',False)], limit=1, order='id desc')

			if sale_id:
				sale_id.order_line.unlink()
				sale_id.write({'order_line': cart_line, 'carrier_id': delivery_id.id})
			else:
				sale_id = env['sale.order'].create({
					'partner_id': partner_id.id,
					'order_line': cart_line,
					'carrier_id': delivery_id.id
				})
			cart_ids.write({'order_id': sale_id.id})
			
			values = {
				'code': 200,
				'status': True,
				'data': {
					'sale_id': sale_id.id
				},
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/check_out', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_check_out(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		sale_obj = env['sale.order']

		company = user_obj.browse(uid).company_id
		if type(body) == str:
			body = json.loads(body)

		if body or headers:
			user_token = headers.get('Authorization')
			user_id = body.get('user_id')
			sale_id = body.get('sale_id')
			point = body.get('point', 0)
			deposit = body.get('deposit', 0)
			payment_id = body.get('payment_id')
			delivery_id = body.get('delivery_id')
			address_type = body.get('address_type')
			custom_address = body.get('custom_address','')
			is_pickup = body.get('is_pickup',False)

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not sale_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				sale = env['sale.order'].browse(int(sale_id))
				if not sale:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not payment_id:
				error['message'] = "Payment method must be filled"
				error['code'] = 400
			else:
				payment = env['payment.provider'].browse(int(payment_id))
				if not payment:
					error['message'] = "Payment method is not registered in the database"
					error['code'] = 400

			if delivery_id:
				delivery = env['delivery.carrier'].search([('id','=',int(delivery_id))])
				if not delivery:
					error['message'] = "Delivery ID is not registered in the database"
					error['code'] = 400

			if not address_type:
				error['message'] = "Address Type must be filled"
				error['code'] = 400
			else:
				if address_type not in ['business','home','custom']:
					error['message'] = "Address Type doesn't match, please choose one of these ['business','home','custom']"
					error['code'] = 400
				if address_type == 'custom':
					if not custom_address:
						error['message'] = "Address Type 'custom', Custom Address must be filled"
						error['code'] = 400
			
			if is_pickup not in [True, False]:
				error['message'] = "Wrong value for is_pickup, please use true (Pickup) or false (not Pickup)"
				error['code'] = 400

			if user:
				user_deposit = user.total_deposit
				if user_deposit < deposit:
					error['message'] = "Non-qualified deposits"
					error['code'] = 400
					
		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner = user.partner_id
			sale_ids = sale_obj.browse(sale.id)
			sale_val = {
				'provider_id': payment.id,
				'total_deposit': deposit,
				'total_point': point,
				'address_type': address_type,
				'custom_address': custom_address
			}
			if payment.is_cod:
				sale_val['is_cod'] = True
			else:
				sale_val['is_cod'] = False

			if delivery_id:
				sale_val['carrier_id'] = int(delivery_id)
			
			if is_pickup == True:
				delivery_id = env['delivery.carrier'].sudo().search([('is_cod','=',True)], limit=1, order='id desc')
				sale_val['carrier_id'] = delivery_id.id

			sale_ids.write(sale_val)
			net_paid = 0
			amount_total = sum(sale_ids.order_line.filtered(lambda p: p.product_id.detailed_type != 'service').mapped('price_subtotal'))
			if (amount_total + sale_ids.total_ongkir - sale_ids.total_discount - point) == deposit:
				sale_ids.action_confirm()
				paid_status = False
			else:
				net_paid = amount_total + sale_ids.total_ongkir - sale_ids.total_discount - point - deposit
				sale_ids.action_check()
				paid_status = True
			values = {
				'code': 200,
				'status': True,
				'data': {
					'sale_id': sale_ids.id,
					'total_ongkir': sale_ids.total_ongkir,
					'total_discount': sale_ids.total_discount*-1 if sale_ids.total_discount > 0 else sale_ids.total_discount,
					'is_not_paid': paid_status,
					'amount_due': net_paid
				},
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/payment', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_payment(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		sale_obj = env['sale.order']

		company = user_obj.browse(uid).company_id
		if type(body) == str:
			body = json.loads(body)
		
		if body or headers:
			user_token = headers.get('Authorization')
			user_id = body.get('user_id')
			sale_id = body.get('sale_id')
			photo = body.get('photo')

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
			
			if not sale_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				sale = env['sale.order'].sudo().search([('id','=',int(sale_id))])
				if not sale:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner = user.partner_id
			if photo:
				image = photo.encode()
				sale.write({
					'transfer_img': image,
				})

			values = {
				'code': 200,
				'status': True,
				'data': {
					'sale_id' : sale.id,
					'sale_name' : sale.name,
				},
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/get_transaction', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_order(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		sale_obj = env['sale.order']

		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			transaction_status = post.get('transaction_status')
			sort = post.get('sort')

			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"
			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

			if sort:
				if sort not in ['asc','desc']:
					error['message'] = 'Wrong value for sort, please use asc or desc'
					error['code'] = 400

			if transaction_status:
				transaction_status = json.loads(transaction_status)
				if transaction_status not in [0,1]:
					error['message'] = 'Wrong value for transaction_status, please use 0 (in_process) or 1 (received)'
					error['code'] = 400
					
		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner = user.partner_id
			order_ids = []
			domain_search = [('partner_id','=',partner.id), ('state', "!=", "draft")]
			if sort:
				sale_ids = sale_obj.search(domain_search, order=f'name {sort}')
			else:
				sale_ids = sale_obj.search(domain_search)

			if transaction_status in [0,1]:
				if transaction_status == 1:
					delivery_status = ['done']
				else:
					delivery_status = ['draft','ready','on_process','on_hold']
				picking_ids = env['stock.picking'].search([('partner_id','=',partner.id),('delivery_status','in',delivery_status),('picking_type_code','=','outgoing')])
				sale_ids = picking_ids.mapped('sale_id')
				if transaction_status == 0:
					sale_checking_ids = sale_obj.search([('partner_id','=',partner.id), ('state', "=", "sent")])
					sale_ids += sale_checking_ids

				if sort:
					if sort == 'asc':
						sale_ids = sale_ids.sorted(key=lambda s: s.name)
					else:
						sale_ids = sale_ids.sorted(key=lambda s: s.name, reverse=True)

			for sale in sale_ids:
				order_line = []
				if sale.state == 'draft':
					state = 'Draft'
				if sale.state == 'sent':
					state = 'Checking Payment'
				if sale.state == 'sale':
					state = 'Confirmed'
				if sale.state == 'done':
					state = 'Done'
				if sale.state == 'cancel':
					state = 'Cancel'

				if sale.order_state == 'dibuat':
					order_state = 1
				elif sale.order_state == 'dikemas':
					order_state = 2
				elif sale.order_state == 'proses':
					order_state = 3
				elif sale.order_state == 'terkirim':
					order_state = 4
				else:
					order_state = 0

				if sale.payment_state == 'paid':
					payment_state = 1
				elif sale.payment_state == 'reversed':
					payment_state = 2
				else:
					payment_state = 0
					
				total_qty = 0
				for line in sale.order_line:
					if line.product_id.detailed_type != 'service':
						order_line.append({
							'id': line.id,
							'product_id': line.product_id.id,
							'product': line.product_id.name,
							'quantity': int(line.product_uom_qty),
							'uom': line.product_uom.name or '',
							'total': line.price_subtotal,
							'type': line.product_id.detailed_type
						})
						total_qty += line.product_uom_qty

				amount_total = sum(sale.order_line.filtered(lambda p: p.product_id.detailed_type != 'service').mapped('price_subtotal'))
				grand_total = amount_total + sale.total_ongkir - sale.total_discount - sale.total_point

				order_ids.append({
					'id': sale.id,
					'customer': sale.partner_id.name,
					'name': sale.name,
					'date_order': (sale.date_order + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') if sale.date_order else '',
					'amount_total': amount_total,
					'deposit': sale.total_deposit,
					'point': sale.total_point*-1 if sale.total_point > 0 else sale.total_point,
					'discount': sale.total_discount*-1 if sale.total_discount > 0 else sale.total_discount,
					'ongkir': sale.total_ongkir,
					'grand_total': grand_total,
					'status': state,
					'transaction_status': 1 if sale.order_state == 'terkirim' else 0,
					'order_state': order_state,
					'payment_state': payment_state,
					'total_qty': int(total_qty),
					'order_line': order_line
				})

			values = {
				'code': 200,
				'status': True,
				'data': order_ids,
				'total_transaction': len(order_ids),
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
		
	@http.route('/api/get_transaction_details', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_transaction_details(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		sale_obj = env['sale.order']

		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			sale_id = post.get('sale_id')
			
			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

			if not sale_id:
				error['message'] = "Sale ID must be filled"
				error['code'] = 400
			else:
				sale_ids = sale_obj.sudo().search([('id','=',int(sale_id))], limit=1)
				if not sale_ids:
					error['message'] = "Sale ID is not registered in the database"
					error['code'] = 400
					
		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner = user.partner_id
			order_ids = {}
			for sale in sale_ids:
				order_line = []
				if sale.state == 'draft':
					state = 'Draft'
				if sale.state == 'sent':
					state = 'Checking Payment'
				if sale.state == 'sale':
					state = 'Confirmed'
				if sale.state == 'done':
					state = 'Done'
				if sale.state == 'cancel':
					state = 'Cancel'

				if sale.order_state == 'dibuat':
					order_state = 1
				elif sale.order_state == 'dikemas':
					order_state = 2
				elif sale.order_state == 'proses':
					order_state = 3
				elif sale.order_state == 'terkirim':
					order_state = 4
				else:
					order_state = 0

				if sale.payment_state == 'paid':
					payment_state = 1
				elif sale.payment_state == 'reversed':
					payment_state = 2
				else:
					payment_state = 0

				invoice_number = ''
				invoice_id = sale.invoice_ids.filtered(lambda p: p.state == 'posted' and p.move_type == 'out_invoice')
				if invoice_id:
					invoice_number = invoice_id[0].name2 or invoice_id[0].name
				
				amount_total = sum(sale.order_line.filtered(lambda p: p.product_id.detailed_type != 'service').mapped('price_subtotal'))
				grand_total = amount_total + sale.total_ongkir - sale.total_discount - sale.total_point

				total_qty = 0
				for line in sale.order_line:
					if line.product_id.detailed_type != 'service':
						discount_data = {}
						is_discount = False
						value = 0
						discount_price = 0
						disc_type = ''
						variant_name = ''
						if line.product_id.product_template_variant_value_ids:
							variant_name = ' - '.join(x.name for x in line.product_id.product_template_variant_value_ids)
						photo = line.product_id.image_1920.decode() if line.product_id.image_1920 else ''

						if line.disc_flat or line.disc_percent:
							is_discount = True
							if line.disc_percent > 0:
								disc_type = 'percent'
								value = line.disc_percent
								discount_price = line.product_id.list_price*(1-line.disc_percent)
							if line.disc_flat > 0:
								disc_type = 'flat'
								value = line.disc_flat
								discount_price = line.product_id.list_price - line.disc_flat
						
						if is_discount:
							discount_data.update({
								'type': disc_type,
								'value': value*100 if value < 1 else value,
								'discount_price': discount_price if discount_price > 0 else 0,
								'total_discounted': line.product_uom_qty*discount_price if discount_price > 0 else 0
							})
						
						order_line.append({
							'id': line.id,
							'product_id': line.product_id.id,
							'product': line.product_id.name,
							'variant_name': variant_name,
							'quantity': int(line.product_uom_qty),
							'uom': line.product_uom.name or '',
							'price_unit': line.price_unit,
							'total': line.price_subtotal,
							'type': line.product_id.detailed_type,
							'is_discount': is_discount,
							'discount': discount_data,
							'image': photo
						})
						total_qty += line.product_uom_qty
					
				order_ids = {
					'id': sale.id,
					'name': sale.name,
					'date_order': (sale.date_order + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') if sale.date_order else '',
					'date_packed': (sale.date_packed + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') if sale.date_packed else '',
					'date_received': (sale.date_received + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') if sale.date_received else '',
					'address_type': sale.address_type or '',
					'full_address': sale.full_address or '',
					'custom_address': sale.custom_address or '',
					'recipient_name': sale.recipient_name or '',
					'payment_info': {
						'provider_id': sale.provider_id.id or '',
						'payment_method': sale.provider_id.name or '',
						'payment_date': sale.payment_date.strftime('%Y-%m-%d %H:%M:%S') if sale.payment_date else '',
						'payment_state': payment_state or ''
					},
					'delivery_info':{
						'delivery_date': (sale.delivery_date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') if sale.delivery_date else '',
						'delivery_done_date': (sale.delivery_done_date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') if sale.delivery_done_date else '',
						'order_state': order_state,
						'delivery_id': sale.carrier_id.id or '',
						'driver': sale.driver_id.name if sale.driver_id else '',
						'is_pickup': True if sale.carrier_id.is_cod else False,
						'pickup_address': sale.carrier_id.pickup_address if sale.carrier_id.is_cod else ''
					},
					'currency': sale.currency_id.name or '',
					'invoice_number': invoice_number,
					'po_number': sale.po_number or '',
					'log_number': sale.log_number or '',
					'term': sale.bp_term_id.name or '',
					'is_cod': sale.is_cod or False,
					'amount_total': amount_total,
					'deposit': sale.total_deposit,
					'point': sale.total_point*-1 if sale.total_point > 0 else sale.total_point,
					'discount': sale.total_discount*-1 if sale.total_discount > 0 else sale.total_discount,
					'ongkir': sale.total_ongkir,
					'grand_total': grand_total,
					'status': state,
					'order_state': order_state,
					'transaction_status': 1 if sale.order_state == 'terkirim' else 0,
					'total_qty': total_qty,
					'order_line': order_line,
					'note': sale.note or ''
				}

			values = {
				'code': 200,
				'status': True,
				'data': order_ids,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/update_transaction', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_update_transaction(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		
		company = user_obj.browse(uid).company_id
		if type(body) == str:
			body = json.loads(body)

		if body:
			user_token = headers.get('Authorization')
			user_id = body.get('user_id')
			sale_id = body.get('sale_id')
			is_received = body.get('is_received',False)
			is_pickup = body.get('is_pickup','is_pickup')

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
					
			if not sale_id:
				error['message'] = "Sale ID must be filled"
				error['code'] = 400
			else:
				sale = env['sale.order'].search([('id', '=', int(sale_id))],limit = 1)
				if not sale:
					error['message'] = "Invalid Sale ID"
					error['code'] = 400

			if is_received not in [True, False]:
				error['message'] = "Wrong value for is_received, please use true (Received) or false (not Received)"        
				error['code'] = 400

			if is_pickup not in [True, False, 'is_pickup']:
				error['message'] = "Wrong value for is_pickup, please use true (Pickup) or false (not Pickup)"        
				error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			if is_received:
				sale.write({'date_received': datetime.now()})
				data = {
					'id': sale.id
				},

			if is_pickup == True:
				delivery_id = env['delivery.carrier'].search([('is_cod','=',True)], limit=1, order='id desc')
				sale.write({'carrier_id': delivery_id.id})

				amount_total = sum(sale.order_line.filtered(lambda p: p.product_id.detailed_type != 'service').mapped('price_subtotal'))
				grand_total = amount_total + sale.total_ongkir - sale.total_discount - sale.total_point
				data = {
					'amount_total': amount_total,
					'ongkir': sale.total_ongkir,
					'point': sale.total_point*-1 if sale.total_point > 0 else sale.total_point,
					'discount': sale.total_discount*-1 if sale.total_discount > 0 else sale.total_discount,
					'grand_total': grand_total
				}
			if is_pickup == False:
				delivery_id = env['delivery.carrier'].search([('is_cod','=',False)], limit=1, order='id desc')
				sale.write({'carrier_id': delivery_id.id})

				amount_total = sum(sale.order_line.filtered(lambda p: p.product_id.detailed_type != 'service').mapped('price_subtotal'))
				grand_total = amount_total + sale.total_ongkir - sale.total_discount - sale.total_point
				data = {
					'amount_total': amount_total,
					'ongkir': sale.total_ongkir,
					'point': sale.total_point*-1 if sale.total_point > 0 else sale.total_point,
					'discount': sale.total_discount*-1 if sale.total_discount > 0 else sale.total_discount,
					'grand_total': grand_total
				}

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/top_up', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_top_up(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		deposit_obj = env['bp.deposit']
		
		company = user_obj.browse(uid).company_id
		if type(body) == str:
			body = json.loads(body)

		if body or headers:
			user_token = headers.get('Authorization')
			user_id = body.get('user_id')
			total = body.get('total')
			payment_id = body.get('payment_id')
				
			if not total:
				error['message'] = "Total must be filled"
				error['code'] = 400
			
			if not payment_id:
				error['message'] = "Payment method must be filled"
				error['code'] = 400
			else:
				payment = env['payment.provider'].browse(int(payment_id))
				if not payment:
					error['message'] = "Payment method is not registered in the database"
					error['code'] = 400

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
					
		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner_id = user.partner_id
			deposit = env['bp.deposit'].create({
				'partner_id': partner_id.id,
				'total': total,
				'payment_id': payment_id,
				'date' : datetime.now()
			})

			values = {
				'code': 200,
				'status': True,
				'data': {
					'id': deposit.id,
					'payment_id': payment_id,
					'total': total,
				},
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/update_top_up', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_update_top_up(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		deposit_obj = env['bp.deposit']
		
		company = user_obj.browse(uid).company_id
		if type(body) == str:
			body = json.loads(body)

		if headers:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

		if body:
			user_id = body.get('user_id')
			photo = body.get('photo')
			deposit_id = body.get('id')
			
			if not photo:
				error['message'] = "Photo must be filled"
				error['code'] = 400
			else:
				image = photo.encode()
			
			if not deposit_id:
				error['message'] = "Deposit ID must be filled"
				error['code'] = 400
			else:
				deposit = env['bp.deposit'].search([('id','=',int(deposit_id))])
				if not deposit:
					error['message'] = "Deposit ID is not registered in the database"
					error['code'] = 400

			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
					
		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner_id = user.partner_id
			deposit = env['bp.deposit'].search([('id', '=', deposit.id),('partner_id','=',partner_id.id)])
			deposit.write({
				'image': image
			})
			deposit.action_to_check()

			values = {
				'code': 200,
				'status': True,
				'data': {
					'id': deposit.id,
				},
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/top_up_history', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_top_up(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		deposit_obj = env['bp.deposit']
		
		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			start_date = post.get('start_date')
			end_date = post.get('end_date')

			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

			if start_date:
				try:
					start_date = datetime.strptime(start_date, '%Y-%m-%d') 
				except:
					error['message'] = 'Start Date format input must be -> YYYY-MM-DD'
					error['code'] = 400

			if end_date:
				try:
					end_date = datetime.strptime(end_date, '%Y-%m-%d') 
				except:
					error['message'] = 'End Date format input must be -> YYYY-MM-DD'
					error['code'] = 400

			if start_date and end_date:
				if (type(start_date) == type(end_date)) and (start_date > end_date):
					error['message'] = 'Start Date must be smaller than End Date'
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner_id = user.partner_id
			domain_search = [('partner_id','=', partner_id.id),('state','in',['used','done'])]
			if start_date and not end_date:
				domain_search += [('date','>=',start_date)]
			if not start_date and end_date:
				domain_search += [('date','<=',end_date)]
			if start_date and end_date:
				domain_search += [('date','>=',start_date),('date','<=',end_date)]

			datas = deposit_obj.search(domain_search)
			data = []
			
			for deposit in datas:
				if deposit.image:
					photo = deposit.image.decode()
				else:
					photo = ''
				data.append({
					"id": deposit.id,
					"name": deposit.name or '',
					"total": deposit.total,
					"partner": deposit.partner_id.name,
					"date": deposit.date.strftime('%Y-%m-%d %H:%M:%S'),
					# "status": deposit.state,
					"image": photo
				})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'total': len(datas),
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/point_history', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_point_history(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		member_point_obj = env['bp.member.point']

		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			start_date = post.get('start_date')
			end_date = post.get('end_date')

			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

			if start_date:
				try:
					start_date = datetime.strptime(start_date, '%Y-%m-%d') 
				except:
					error['message'] = 'Start Date format input must be -> YYYY-MM-DD'
					error['code'] = 400

			if end_date:
				try:
					end_date = datetime.strptime(end_date, '%Y-%m-%d') 
				except:
					error['message'] = 'End Date format input must be -> YYYY-MM-DD'
					error['code'] = 400

			if start_date and end_date:
				if (type(start_date) == type(end_date)) and (start_date > end_date):
					error['message'] = 'Start Date must be smaller than End Date'
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner_id = user.partner_id
			domain_search = [('partner_id','=', partner_id.id)]
			if start_date and not end_date:
				domain_search += [('date','>=',start_date)]
			if not start_date and end_date:
				domain_search += [('date','<=',end_date)]
			if start_date and end_date:
				domain_search += [('date','>=',start_date),('date','<=',end_date)]

			datas = member_point_obj.search(domain_search, order='date asc')
			data = []
			
			for member_point in datas:
				data.append({
					"id": member_point.id,
					"name": member_point.name or '',
					"point": member_point.point,
					"partner": member_point.partner_id.name,
					"date": member_point.date.strftime('%Y-%m-%d %H:%M:%S') if member_point.date else '',
				})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'total': len(datas),
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/payment_method', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_payment_method(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		payment_provider_obj = env['payment.provider']
		
		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or body:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')

			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"		

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"		

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			datas = payment_provider_obj.search([('code', '=', 'custom')])
			data = {
				'is_deposit': [],
				'is_credit': [],
				'is_bank': [],
				'is_cod': [],
				'is_cash': []
			}
			
			for payment_provider in datas:
				if payment_provider.image_128:
					image = payment_provider.image_128.decode()
				else:
					image = ''
				
				payment_data = {
					"id": payment_provider.id,
					"name": payment_provider.name,
					"description": payment_provider.description or '',
					"account_name": payment_provider.acc_name or '',
					"account_number": payment_provider.acc_number or '',
					"icon": image,
				}
				
				if payment_provider.is_deposit:
					data['is_deposit'].append(payment_data)
				if payment_provider.is_credit:
					data['is_credit'].append(payment_data)
				if payment_provider.is_bank:
					data['is_bank'].append(payment_data)
				if payment_provider.is_cod:
					data['is_cod'].append(payment_data)
				if payment_provider.is_cash:
					data['is_cash'].append(payment_data)

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/delivery_method', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_delivery_method(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		delivery_carrier_obj = env['delivery.carrier']
		
		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')

			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			datas = delivery_carrier_obj.search([])
			data = []
			
			for delivery_carrier in datas:
				data.append({
					"id": delivery_carrier.id,
					"name": delivery_carrier.name or '',
				})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	#Driver
	
	@http.route('/api/order_job', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_delivery_order(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		
		company = user_obj.browse(uid).company_id

		if headers or post:
			job_status = post.get('job_status')
			user_token = headers.get('Authorization')
			is_ready = post.get('is_ready',False)
			
			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"
			
			if job_status:
				job_status = json.loads(job_status)
				if type(job_status) != int:
					error['message'] = "Wrong value for job_status, use 0 or 1"
					error['code'] = 400

			if is_ready:
				try:
					is_ready = json.loads(is_ready)
				except:
					error['message'] = "Error. Wrong value for is_ready, please use true or false"
					error['code'] = 400
				if is_ready not in [True, False]:
					error['message'] = "Wrong value for is_ready, please use true or false"
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			delivery_status = []
			if job_status == 1:
				delivery_status = ['done']
			if job_status == 0:
				# delivery_status = ['draft','ready','on_process','on_hold']
				delivery_status = ['on_process']
			if is_ready:
				delivery_status = ['ready']
			
			if delivery_status:
				datas = env['stock.picking'].search([('driver_id', '=', user.id),('picking_type_code','=','outgoing'),('state','!=','cancel'),('delivery_status','in',delivery_status)])
			else:
				datas = env['stock.picking'].search([('driver_id', '=', user.id),('picking_type_code','=','outgoing'),('state','!=','cancel')])
			data = []
			for delivery_order in datas:
				data.append({
					"id": delivery_order.id,
					"name": delivery_order.name,
					"customer_name": delivery_order.partner_id.name or '',
					"address": delivery_order.sale_id.full_address or delivery_order.sale_id.custom_address or '',
					"job_status" :1 if delivery_order.delivery_status == 'done' else 0,
					"is_ready": True if delivery_order.delivery_status == 'ready' else False,
					"delivery_carrier" : delivery_order.carrier_id.name or '',
					"delivery_date" : delivery_order.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if delivery_order.scheduled_date else '',
					"shipping_fee": delivery_order.sale_id.total_ongkir
				})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/order_job_details', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_get_delivery_order_details(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		
		company = user_obj.browse(uid).company_id
		# if type(body) == str:
		# 	body = json.loads(body)

		if headers or post:
			# user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			job_id = post.get('job_id')
			
			# if not user_id:
			# 	error['message'] = "User ID must be filled"
			# else:
			# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
			# 	if not user:
			# 		error['message'] = "User ID is not registered in the database"

			# if not user_token:
			# 	error['message'] = "Token must be filled"
			# else:
			# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
			# 	if not token:
			# 		error['message'] = "Invalid user_token"

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

			if not job_id:
				error['message'] = "Job ID must be filled"
				error['code'] = 400
			else:
				job = env['stock.picking'].search([('id', '=', job_id)],limit = 1)
				if not job:
					error['message'] = "Invalid job_id"
					error['code'] = 400
			
		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			datas = env['stock.picking'].browse(int(job_id))
			data = []
			order_line = []
			for delivery_order in datas:
				
				if datas.driver_img:
					image = datas.driver_img.decode()
				else:
					image = ''
				
				for line in delivery_order.sale_id.order_line:
					variant_name = ''
					if line.product_id.product_template_variant_value_ids:
						variant_name = ' - '.join(x.name for x in line.product_id.product_template_variant_value_ids)

					if line.product_id.detailed_type != 'service':
						order_line.append({
							'product_id': line.product_id.id,
							'product': line.product_id.name,
							'variant_name': variant_name,
							'quantity': int(line.product_uom_qty),
							'price_unit': line.price_unit,
							'uom': line.product_uom.name or '',
							'subtotal': line.price_total
						})
				
				invoice_number = ''
				if delivery_order.sale_id:
					invoice_id = delivery_order.sale_id.invoice_ids.filtered(lambda p: p.state == 'posted' and p.move_type == 'out_invoice')
					if invoice_id:
						invoice_number = invoice_id[0].name2 or invoice_id[0].name

				amount_total = 0
				grand_total = 0
				payment_state = 0
				if delivery_order.sale_id:
					amount_total = sum(delivery_order.sale_id.order_line.filtered(lambda p: p.product_id.detailed_type != 'service').mapped('price_subtotal'))
					grand_total = amount_total + delivery_order.sale_id.total_ongkir - delivery_order.sale_id.total_discount - delivery_order.sale_id.total_point

					if delivery_order.sale_id.payment_state == 'paid':
						payment_state = 1
					elif delivery_order.sale_id.payment_state == 'reversed':
						payment_state = 2
					else:
						payment_state = 0

				data = {                            
					"name": delivery_order.name,
					"transaction": delivery_order.sale_id.name or '',
					"invoice": invoice_number,
					"customer_name": delivery_order.partner_id.name or '',
					"address_type": delivery_order.sale_id.address_type or '',
					"address": delivery_order.sale_id.full_address or delivery_order.sale_id.custom_address or '',
					"delivery_status" : delivery_order.delivery_status or '',
					"is_cod": delivery_order.sale_id.is_cod or False,
					"latitude" : delivery_order.partner_id.partner_latitude,
					"longitude" : delivery_order.partner_id.partner_longitude,
					"phone" : delivery_order.partner_id.phone or '',
					"delivery_name": delivery_order.sale_id.carrier_id.name or '',
					"image": image,
					"order_line": order_line,
					"payment": {
						"total": amount_total,
						"ongkir": delivery_order.sale_id.total_ongkir or 0,
						"point": (delivery_order.sale_id.total_point*-1 if delivery_order.sale_id.total_point > 0 else delivery_order.sale_id.total_point) or 0,
						"discount": (delivery_order.sale_id.total_discount*-1 if delivery_order.sale_id.total_discount > 0 else delivery_order.sale_id.total_discount) or 0,
						"grand_total": grand_total,
						"payment_state": payment_state,
						"payment_method": delivery_order.sale_id.provider_id.name or '',
						"note": delivery_order.sale_id.note or ''
					},
					"logs": {
						"driver_name": delivery_order.driver_id.name or '',
						"date_received": (delivery_order.sale_id.date_received + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') if delivery_order.sale_id.date_received else '',
						"delivery_date" : (delivery_order.scheduled_date + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') if delivery_order.scheduled_date else '',
						"delivery_date_done" : (delivery_order.date_done + timedelta(hours=7)).strftime('%Y-%m-%d %H:%M:%S') if delivery_order.date_done else ''
					}
				}

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
	
	@http.route('/api/update_order_job', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_update_order_job(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		company = user_obj.browse(uid).company_id
		if type(body) == str:
			body = json.loads(body)

		if body:
			user_token = headers.get('Authorization')
			user_id = body.get('user_id')
			job_id = body.get('job_id')
			photo = body.get('photo')
			on_hold = body.get('on_hold')
			on_process = body.get('on_process')
			is_done = body.get('is_done',False)
			is_cod = body.get('is_cod',False)
			
			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
					
			if not job_id:
				error['message'] = "Job ID must be filled"
				error['code'] = 400
			else:
				job = env['stock.picking'].search([('id', '=', int(job_id))],limit = 1)
				if not job:
					error['message'] = "Invalid Job ID"
					error['code'] = 400

			if is_done not in [True, False]:
				error['message'] = "Wrong value for is_done, please use true (Done) or false (not Done)"
				error['code'] = 400

			if is_cod not in [True, False]:
				error['message'] = "Wrong value for is_cod, please use true or false"
				error['code'] = 400

			if is_cod == True:
				if not job.sale_id.is_cod:        
					error['message'] = "Transaction is not COD"
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			datas = job
			if on_hold:
				datas.write({
					'delivery_status' : 'on_hold'
				})
			if on_process:
				datas.write({
					'delivery_status' : 'on_process',
					'scheduled_date': datetime.now()
				})
			if photo:
				image = photo.encode()
				datas.write({
					'driver_img':image
				})
			
			if is_done == True:
				if datas.state not in ['cancel','done']:
					datas.button_validate()

			if is_cod == True:
				for invoice in job.sale_id.invoice_ids.filtered(lambda p: p.state == 'posted' and p.move_type == 'out_invoice' and p.payment_state == 'not_paid'):
					invoice.create_payment_from_api()
				if datas.state not in ['cancel','done']:
					datas.button_validate()

			values = {
				'code': 200,
				'status': True,
				'data': {
					'id': datas.id
				},
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/negotiation', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_negotiation(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		body = request.httprequest.data                
		body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		
		company = user_obj.browse(uid).company_id
		if type(body) == str:
			body = json.loads(body)
		
		if body or headers:
			user_token = headers.get('Authorization')
			user_id = body.get('user_id')
			sale_id = body.get('sale_id')
			message = body.get('message')
			# line_ids = body.get('line_ids')
			
			if not user_id:
				error['message'] = "User ID must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
				if not user:
					error['message'] = "User ID is not registered in the database"
					error['code'] = 400

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not sale_id:
				error['message'] = "Sale ID must be filled"
				error['code'] = 400
			else:
				sale = env['sale.order'].search([('id','=',int(sale_id))])
				if not sale:
					error['message'] = "Invalid Sale ID"
					error['code'] = 400  

			if not message:
				error['message'] = "Message must be filled"
				error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner_id = user.partner_id
			negotiation_id = env['bp.negotiation'].create({
				'sale_id': sale.id,
				'date': datetime.now(),
				'partner_id': partner_id.id,
				'message': message,
				'state': 'check'
			})
			values = {
				'code': 200,
				'status': True,
				'data': {
					'sale_id': sale.id,
					'negotiation_id': negotiation_id.id
				},
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/pdf/invoice', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_pdf_invoice(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		user_obj = env['res.users']
		headers = request.httprequest.headers
		error = {'code': 401, 'status': False}
		values = {}
		data = {}

		# user_id = post.get('user_id')
		user_token = headers.get('Authorization')
		sale_id = post.get('sale_id',False)

		# if not user_id:
		# 	error['message'] = "User ID must be filled"
		# else:
		# 	user = user_obj.sudo().search([('id','=',int(user_id))], limit=1)
		# 	if not user:
		# 		error['message'] = "User ID is not registered in the database"

		# if not user_token:
		# 	error['message'] = "Token must be filled"
		# else:
		# 	token = user_obj.sudo().search([('id','=',int(user_id)),('token_api', '=', user_token)],limit = 1)
		# 	if not token:
		# 		error['message'] = "Invalid user_token"
		if not user_token:
			error['message'] = "Token must be filled"
			error['code'] = 400
		else:
			user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
			if not user:
				error['message'] = "Invalid user_token"

		if not sale_id:
			error['message'] = "Sale ID must be filled"
			error['code'] = 400
		else:
			sale = env['sale.order'].search([('id','=',int(sale_id))])
			if not sale:
				error['message'] = "Invalid Sale ID"
				error['code'] = 400
			else:
				if not sale.invoice_ids:
					error['message'] = "Invoice not found or created" 
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			pdf_merger = PdfFileMerger()
			for invoice in sale.invoice_ids.filtered(lambda p: p.state == 'posted' and p.move_type == 'out_invoice'):
				pdf_content, _ = env['ir.actions.report'].sudo()._render_qweb_pdf('account.report_invoice_with_payments', [invoice.id])
				# pdf_content = invoice.with_context(from_api=True).invoice_html2pdf()
				pdf_merger.append(io.BytesIO(pdf_content), import_bookmarks=False)

			pdf_output = io.BytesIO()
			pdf_merger.write(pdf_output)
			pdf_merger.close()

			pdf_filename = f"Invoice_{sale.name}.pdf"
			headers = [
				('Content-Type', 'application/pdf'),
				('Content-Length', len(pdf_output.getvalue())),
				('Content-Disposition', content_disposition(pdf_filename)),
			]
			report_pdf = request.make_response(pdf_output.getvalue(), headers=headers)
			return report_pdf

		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/history_transaction', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_history_transaction(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		
		company = user_obj.browse(uid).company_id

		if headers or post:
			user_token = headers.get('Authorization')
			name = post.get('search','')
			category_ids = post.get('category_ids',[])
			updated = post.get('updated')
			sort = post.get('sort')
			page = int(post.get('page', 1))
			limit = int(post.get('limit', 5))
			offset = (page - 1) * limit

			if not user_token:
				error['message'] = "Token must be filled"
				error['code'] = 400
			else:
				user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
				if not user:
					error['message'] = "Invalid user_token"

			if category_ids:
				category_ids = json.loads(category_ids)
				if type(category_ids) != list:
					error['message'] = "Category IDs must type List [id1,id2,..]"
					error['code'] = 400

			if sort:
				if sort not in ['asc','desc']:
					error['message'] = 'Wrong value for sort, please use asc or desc'
					error['code'] = 400

			if updated:
				try:
					updated = json.loads(updated)
					if updated not in [0,1]:
						error['message'] = 'Wrong value for updated, please 0 or 1'
						error['code'] = 400
				except:
					error['message'] = 'Wrong value for updated, please 0 or 1'
					error['code'] = 400

		if error.get('message'):
			values = error
			return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		else:
			partner_id = user.partner_id
			data = []
			domain_search = [
				('order_id.partner_id','=',partner_id.id),
				('order_id.state','in',['sale','done']),
				('order_id','!=',False),
				('product_id.detailed_type','!=','service')
			]
			if name:
				domain_search += [('product_id.name','ilike',name)]
			if category_ids and type(category_ids) == list:
				domain_search += [('product_id.categ_id','in',category_ids)]

			if sort:
				order_line_ids = env['sale.order.line'].sudo().search(domain_search, limit=limit, offset=offset, order=f"name {sort}")
			else:
				order_line_ids = env['sale.order.line'].sudo().search(domain_search, limit=limit, offset=offset)
			
			if updated == 0:
				order_line_ids = order_line_ids.sorted(key=lambda s: s.product_id.write_date)
			if updated == 1:
				order_line_ids = order_line_ids.sorted(key=lambda s: s.product_id.write_date, reverse=True)

			for line in order_line_ids:
				updated_price = ''
				if line.product_id.last_price:
					if line.product_id.list_price < line.price_unit:
						updated_price = 'down'
					if line.product_id.list_price > line.price_unit:
						updated_price = 'up'

				variant_name = ''
				if line.product_id.product_template_variant_value_ids:
					variant_name = ' - '.join(x.name for x in line.product_id.product_template_variant_value_ids)

				data.append({
					'product_id': line.product_id.id,
					'image': line.product_id.image_1920.decode() if line.product_id.image_1920 else '',
					'name': line.product_id.name,
					'variant_name': variant_name,
					'price': line.price_unit,
					'updated_price': updated_price,
					'category':{
						'id': line.product_id.categ_id.id,
						'name': line.product_id.categ_id.name
					},
				})

			values = {
				'code': 200,
				'status': True,
				'data': data,
				'pagination': {
					'page': page,
					'limit': limit
				},
				'message': 'Success'
			}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/shop', methods=['GET'], type='http', auth="public", csrf=False, website=True)
	def api_shop(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		headers = request.httprequest.headers
		user_obj = env['res.users']

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		
		company = user_obj.browse(uid).company_id

		# if headers or post:
		# 	user_token = headers.get('Authorization')

		# 	if not user_token:
		# 		error['message'] = "Token must be filled"
		# 		error['code'] = 400
		# 	else:
		# 		user = user_obj.sudo().search([('token_api','=',user_token)], limit=1)
		# 		if not user:
		# 			error['message'] = "Invalid user_token"

		# if error.get('message'):
		# 	values = error
		# 	return Response(json.dumps(values), status=values.get('code'), headers={'Access-Control-Allow-Origin': '*'})
		# else:
		# data = {}
		if company:
			delivery_id = env['delivery.carrier'].sudo().search([('is_cod','=',True)], limit=1, order='id desc')
			if delivery_id:
				data = {
					'pickup_address': delivery_id.pickup_address,
					'phone': company.phone
				}
			
		values = {
			'code': 200,
			'status': True,
			'data': data,
			'message': 'Success'
		}
		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)
