from datetime import datetime
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
			if not password:
				error['message'] = "Password must be filled"

			try:
				uid = request.session.authenticate(request.db, username, password)
			except:
				uid = False

			if not uid:
				error['message'] = "Wrong username or password"

			if error.get('message'):
				values = error
			else:
				user = user_obj.sudo().browse(uid)
				partner = user.partner_id
				user.create_token_api()
				values = {
					'code': 200,
					'status': True,
					'data':{
						'user_id': user.id,
						'user_type': partner.user_type if user.share else 'admin',
						'name': user.name,
						'user_token': user.token_api
					},
					'message': "You are successfully login"
				}
		else:
			error['message'] = "Empty params"
			values = error

		headers = {'Access-Control-Allow-Origin': '*'}
		return Response(json.dumps(values), headers=headers)

	@http.route('/api/logout', methods=['POST'], type='http', auth="public", csrf=False, website=True)
	def api_logout(self, **post):
		cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
		request.update_env(user=odoo.SUPERUSER_ID)
		env = request.env
		# body = request.httprequest.data
		# body = json.loads(body)
		# if type(body) == str:
		# 	body = json.loads(body)
		headers = request.httprequest.headers
		error = {'code': 401, 'status': False}
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		company = user_obj.browse(uid).company_id

		values = {}

		if headers:
			user_token = headers.get('Authorization')
			if not user_token:
				error['message'] = "User Token must be filled"
			else: 
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
		else:
			error['message'] = "Headers empty"
				
		if error.get('message'):
				values = error
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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			
			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user_token:
					error['message'] = "Token must be filled"
				else:
					if user_token != user.token_api:
						error['message'] = "Invalid user_token"
				if not user:
					error['message'] = "User ID is not registered in the database"

		if error.get('message'):
				values = error
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
					'name': partner.name or '',
					'address': partner.full_address or '',
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

		if headers:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
		
		if body:
			photo = body.get('photo')
			name = body.get('name')
			email = body.get('email')
			phone = body.get('phone')
			user_id = body.get('user_id')
			update_profile = {}

			if not photo:
				error['message'] = "Photo must be filled"
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
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					partner = user.partner_id
					if partner:
						partner.write(update_profile)

		if error.get('message'):
				values = error
		else:
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

		if headers:
			user_token = headers.get('Authorization')
			if not user_token:
				error['message'] = "Token must be filled"
			else:
				datas = bp_promotion_obj.search([])
				data = []
				
				for promotion in datas:
					state = promotion.state
					if state == "open":
						if promotion.is_all_product:
							products = env['product.product'].search([('detailed_type', '!=', 'service')])
							image = promotion.image.decode()
							data.append({
								"id": promotion.id,
								"nama": promotion.name or '',
								"image": image or '',
								"disc_type" : promotion.disc_type or '',
								"disc_flat" : promotion.disc_flat or 0,
								"disc_percent" : promotion.disc_percent or 0,
								"is_all_product" : promotion.is_all_product,
								"state" : promotion.state or '',
								"product_ids" : [product.id for product in products] or [],
								"start_date" : promotion.start_date.strftime('%Y-%m-%d %H:%M:%S') if promotion.start_date else '',
								"end_date" : promotion.end_date.strftime('%Y-%m-%d %H:%M:%S') if promotion.end_date else ''
							})
						else :
							image = promotion.image.decode()
							data.append({
								"id": promotion.id,
								"nama": promotion.name or '',
								"image": image or '',
								"disc_type" : promotion.disc_type or '',
								"disc_flat" : promotion.disc_flat or 0,
								"disc_percent" : promotion.disc_percent or 0,
								"is_all_product" : promotion.is_all_product,
								"state" : promotion.state or '',
								"product_ids" : [x.product_id.id for x in promotion.line_ids] or [],
								"start_date" : promotion.start_date.strftime('%Y-%m-%d %H:%M:%S') if promotion.start_date else '',
								"end_date" : promotion.end_date.strftime('%Y-%m-%d %H:%M:%S') if promotion.end_date else ''
							})
		if error.get('message'):
				values = error
		else:
			values = {
				'code': 200,
				'status': True,
				'data': data,
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
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		
		company = user_obj.browse(uid).company_id
		
		# if isinstance(body, str):
		# 	body = json.loads(body)

		error = {'code': 401, 'status': False}
		values = {}
		data = []

		user_id = post.get('user_id')
		user_token = headers.get('Authorization')

		if not user_token:
			error['message'] = "Token must be filled"
		else:
			token = user_obj.search([('token_api', '=', user_token)], limit=1)
			if not token:
				error['message'] = "Invalid user_token"

		if not user_id:
			error['message'] = "User ID must be filled"
		else:
			user = user_obj.browse(int(user_id))
			if not user:
				error['message'] = "User ID is not registered in the database"
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
						'segment_id': product.segment_ids.ids or [],
						'image': photo,
					})

		if 'message' in error:
			values = error
		else:
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
			user_token = headers.get('Authorization')
			segment_ids = post.get('segment_ids')

			if not segment_ids:
				error['message'] = "Segment IDs must be filled"
			else:
				segment_ids = json.loads(segment_ids)
				if type(segment_ids) != list:
					error['message'] = "Segment IDs must type List [id1,id2,..]"

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)], limit=1)
				if not token:
					error['message'] = "Invalid user_token"
				else:
					datas = product_segment_obj.search([('id','in',segment_ids)])
					data = []
					
					for segment in datas:
						image = segment.icon_img.decode() if segment.icon_img else ''
						data.append({
							"id": segment.id,
							"nama": segment.name or '',
							"image": image
						})

		if error.get('message'):
				values = error
		else:
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
			user_token = headers.get('Authorization')
			segment_ids = post.get('segment_ids')

			if not segment_ids:
				error['message'] = "Segment IDs must be filled"
			else:
				segment_ids = json.loads(segment_ids)
				if type(segment_ids) != list:
					error['message'] = "Segment IDs must type List [id1,id2,..]"

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)], limit=1)
				if not token:
					error['message'] = "Invalid user_token"

		if error.get('message'):
				values = error
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
					"nama": categ.name or '',
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
		# body = request.httprequest.data                
		# body = json.loads(body)
		headers = request.httprequest.headers
		user_obj = env['res.users']
		partner_obj = env['res.partner']
		
		company = user_obj.browse(uid).company_id
		
		# if isinstance(body, str):
		# 	body = json.loads(body)

		error = {'code': 401, 'status': False}
		values = {}
		data = []

		name = post.get('search','')
		user_id = post.get('user_id')
		user_token = headers.get('Authorization')
		page = int(post.get('page', 1))
		limit = int(post.get('limit', 5))
		offset = (page - 1) * limit
		segment_ids = post.get('segment_ids',[])
		category_ids = post.get('category_ids',[])
		min_price = post.get('min_price')
		max_price = post.get('max_price')

		if not segment_ids:
			error['message'] = "Segment IDs must be filled"
		else:
			segment_ids = json.loads(segment_ids)
			if type(segment_ids) != list:
				error['message'] = "Segment IDs must type List [id1,id2,..]"

		if category_ids:
			category_ids = json.loads(category_ids)
			if type(category_ids) != list:
				error['message'] = "Category IDs must type List [id1,id2,..]"

		if not user_token:
			error['message'] = "Token must be filled"
		else:
			token = user_obj.sudo().search([('token_api', '=', user_token)], limit=1)
			if not token:
				error['message'] = "Invalid user_token"

		if not user_id:
			error['message'] = "User ID must be filled"
		else:
			user = user_obj.sudo().browse(int(user_id))
			if not user:
				error['message'] = "User ID is not registered in the database"
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

				product_ids = env['product.product'].sudo().search(domain_search, limit=limit, offset=offset)
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
					data.append({
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
						"description": product.description or ''
					})

		if 'message' in error:
			values = error
		else:
			values = {
				'code': 200,
				'status': True,
				'data': data,
				'pagination': {
					'page': page,
					'limit': limit,
					'total_items': len(product_ids)
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
				
		# if isinstance(body, str):
		# 	body = json.loads(body)

		error = {'code': 401, 'status': False}
		values = {}
		data = []

		user_id = post.get('user_id')
		product_id = post.get('product_id')
		user_token = headers.get('Authorization')

		if not user_token:
			error['message'] = "Token must be filled"
		else:
			token = user_obj.sudo().search([('token_api', '=', user_token)], limit=1)
			if not token:
				error['message'] = "Invalid user_token"

		if not user_id:
			error['message'] = "User ID must be filled"
		else:
			user = user_obj.sudo().browse(int(user_id))
			if not user:
				error['message'] = "User ID is not registered in the database"

		if not product_id:
			error['message'] = "Product ID must be filled"
		else:
			product_ids = product_obj.sudo().browse(int(product_id))
			if not product_ids:
				error['message'] = "Product ID is not registered in the database"					

		if 'message' in error:
			values = error
		else:
			partner = user.partner_id
			
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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.sudo().search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.sudo().browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					partner_id = user.partner_id
					datas = favorite_product_obj.search([('partner_id','=', partner_id.id)])
					data = []
					
					for favorite_product in datas:
						if favorite_product.image:
							photo = favorite_product.image.decode()
						else:
							photo = ''

						data.append({
							"id": favorite_product.id,
							"nama": favorite_product.product_id.name or '',
							"image": photo,
						})

		if error.get('message'):
				values = error
		else:
			values = {
				'code': 200,
				'status': True,
				'data': data,
				'message': 'Success'
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

		if headers:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
		
		if body:
			user_id = body.get('user_id')
			product_id = body.get('product_id')
			
			if not product_id:
				error['message'] = "Product must be filled"
			else: 
				product_id = env['product.product'].browse(int(product_id))
				if not product_id:
					error['message'] = "Product is not registered in the database"
			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					favorite_product_id = env['bp.favorite.product'].create({
						'product_id': product_id.id,
						'partner_id': user.partner_id.id
					})

		if error.get('message'):
				values = error
		else:
			values = {
				'code': 200,
				'status': True,
				'data':{
					'favorite_product' : favorite_product_id.id
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
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
			if not product_id:
				error['message'] = "Product must be filled"
			else: 
				product_id = env['product.product'].browse(int(product_id))
				if not product_id:
					error['message'] = "Product is not registered in the database"
			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					partner_id = user.partner_id
					favorite_product_id = env['bp.favorite.product'].search([('product_id','=',product_id.id),('partner_id','=',partner_id.id)])
					favorite_product_id.unlink()

		if error.get('message'):
				values = error
		else:
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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				
		if error.get('message'):
				values = error
		else:
			partner_id = user.partner_id
			cart_line = []
			cart_ids = env['bp.cart'].search([('partner_id','=',partner_id.id),('state','in',[False, 'draft'])], order='id desc')

			for cart in cart_ids:
				variant_name = ''
				if cart.product_id.product_template_variant_value_ids:
					variant_name = ' - '.join(x.name for x in cart.product_id.product_template_variant_value_ids)

				cart_line.append({
					'cart_id': cart.id,
					'product_id': cart.product_id.id,
					'name': cart.product_id.name,
					'price': cart.product_id.list_price,
					'variant_name': variant_name,
					'product_uom_qty': cart.product_uom_qty
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

		if headers:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
		
		if body:
			user_id = body.get('user_id')
			product_id = body.get('product_id')
			product_uom_qty = body.get('product_uom_qty')

			if not product_id:
				error['message'] = "Product must be filled"
			else: 
				product_id = env['product.product'].browse(int(product_id))
				if not product_id:
					error['message'] = "Product is not registered in the database"
			if not user_id:
				error['message'] = "User must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User is not registered in the database"
		if error.get('message'):
				values = error
		else:
			partner_id = user.partner_id
			cart_id = env['bp.cart'].search([('partner_id','=', partner_id.id),('product_id','=',product_id.id)])
			if cart_id:
				up_quantity = product_uom_qty or (cart_id.product_uom_qty + 1)
				cart_id.write({'product_uom_qty': up_quantity})
			else: 
				cart_id = env['bp.cart'].create({
					'name': product_id.name,
					'partner_id': partner_id.id,
					'product_id': product_id.id,
					'product_uom_qty': product_uom_qty or 1
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
			
			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"

			if not cart_id:
				error['message'] = "Cart ID must be filled"
			else:
				cart = env['bp.cart'].search([('id','=',int(cart_id))], limit=1)
				if not cart:
					error['message'] = "Cart ID is not registered in the database"

		if error.get('message'):
				values = error
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

		if headers:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
		
		if body:
			user_id = body.get('user_id')
			cart_ids = body.get('cart_ids',[])

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"

			if not cart_ids:
				error['message'] = "Cart IDs must be filled"
			else:
				if type(cart_ids) != list:
					error['message'] = "Cart IDs must type List [id1,id2,..]"

		if error.get('message'):
				values = error
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
							'product_uom_qty': cart.product_uom_qty})
				)

			sale_id = env['sale.order'].search([('partner_id','=',partner_id.id),('state','=','draft')], limit=1, order='id desc')

			if sale_id:
				sale_id.order_line.unlink()
				sale_id.write({'order_line': cart_line})
			else:
				sale_id = env['sale.order'].create({
					'partner_id': partner_id.id,
					'order_line': cart_line
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

		if headers:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
		
		if body:
			user_id = body.get('user_id')
			sale_id = body.get('sale_id')
			point = body.get('point', 0)
			deposit = body.get('deposit', 0)
			payment_id = body.get('payment_id')
			delivery_id = body.get('delivery_id')
			address_type = body.get('address_type')
			custom_address = body.get('custom_address','')

			if not sale_id:
				error['message'] = "User ID must be filled"
			else:
				sale = env['sale.order'].browse(int(sale_id))
				if not sale:
					error['message'] = "User ID is not registered in the database"

			if not payment_id:
				error['message'] = "Payment method must be filled"
			else:
				payment = env['payment.provider'].browse(int(payment_id))
				if not payment:
					error['message'] = "Payment method is not registered in the database"

			if not delivery_id:
				error['message'] = "Delivery carrier must be filled"
			else:
				delivery = env['delivery.carrier'].browse(int(delivery_id))
				if not delivery:
					error['message'] = "Delivery carrier is not registered in the database"

			if not address_type:
				error['message'] = "Address Type must be filled"
			else:
				if address_type not in ['business','home','custom']:
					error['message'] = "Address Type doesn't match, please choose one of these ['business','home','custom']"
				if address_type == 'custom':
					if not custom_address:
						error['message'] = "Address Type 'custom', Custom Address must be filled"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
					
		if error.get('message'):
				values = error
		else:
			partner = user.partner_id
			user_deposit = user.total_deposit
			if user_deposit < deposit:
				error['message'] = "Non-qualified deposits"
			sale_ids = sale_obj.browse(sale.id)
			sale_ids.write({
				'provider_id': payment.id,
				'carrier_id': delivery.id,
				'total_deposit': deposit,
				'total_point': point,
				'address_type': address_type,
				'custom_address': custom_address
			})
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

		if headers:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
		
		if body:
			user_id = body.get('user_id')
			sale_id = body.get('sale_id')
			photo = body.get('photo')
			
			if not sale_id:
				error['message'] = "User ID must be filled"
			else:
				sale = env['sale.order'].browse(int(sale_id))
				if not sale:
					error['message'] = "User ID is not registered in the database"
			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					partner = user.partner_id
					if photo:
						image = photo.encode()
						sale.write({
							'transfer_img': image,
						})

		if error.get('message'):
			values = error
		else:
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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			transaction_status = post.get('transaction_status')
			sort = post.get('sort')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if sort:
				if sort not in ['asc','desc']:
					error['message'] = 'Wrong value for sort, please use asc or desc'

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					partner = user.partner_id
					order_ids = []
					domain_search = [('partner_id','=',partner.id), ('state', "!=", "draft")]
					if sort:
						sale_ids = sale_obj.search(domain_search, order=f'name {sort}')
					else:
						sale_ids = sale_obj.search(domain_search)

					if transaction_status:
						if transaction_status == 1:
							delivery_status = ['done']
						else:
							delivery_status = ['draft','ready','on_process','on_hold']
						picking_ids = env['stock.picking'].search([('partner_id','=',partner.id),('delivery_status','in',delivery_status),('picking_type_code','=','outgoing')])
						sale_ids = picking_ids.mapped('sale_id')

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
						order_ids.append({
							'id': sale.id,
							'customer': sale.partner_id.name,
							'name': sale.name,
							'date_order': sale.date_order.strftime('%Y-%m-%d %H:%M:%S'),
							'amount_total': sale.amount_total,
							'status': state,
							'transaction_status': 1 if sale.order_state == 'terkirim' else 0,
							'order_state': order_state,
							'payment_state': payment_state,
							'order_line': order_line
						})

		if error.get('message'):
				values = error
		else:
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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			sale_id = post.get('sale_id')
			
			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					partner = user.partner_id
					order_ids = {}
					sale_ids = sale_obj.browse(int(sale_id))
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

						for line in sale.order_line:
							if line.product_id.detailed_type != 'service':
								variant_name = ''
								if line.product_id.product_template_variant_value_ids:
									variant_name = ' - '.join(x.name for x in line.product_id.product_template_variant_value_ids)

								order_line.append({
									'id': line.id,
									'product_id': line.product_id.id,
									'product': line.product_id.name,
									'variant_name': variant_name,
									'quantity': int(line.product_uom_qty),
									'uom': line.product_uom.name or '',
									'price_unit': line.price_unit,
									'total': line.price_subtotal,
									'type': line.product_id.detailed_type
								})
							
						order_ids = {
							'id': sale.id,
							'name': sale.name,
							'date_order': sale.date_order.strftime('%Y-%m-%d %H:%M:%S') if sale.date_order else '',
							'date_packed': sale.date_packed.strftime('%Y-%m-%d %H:%M:%S') if sale.date_packed else '',
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
								'delivery_date': sale.delivery_date.strftime('%Y-%m-%d %H:%M:%S') if sale.delivery_date else '',
								'delivery_done_date': sale.delivery_done_date.strftime('%Y-%m-%d %H:%M:%S') if sale.delivery_done_date else '',
								'order_state': order_state,
								'delivery_id': sale.carrier_id.id or '',
								'driver': sale.driver_id.name if sale.driver_id else ''
							},
							'currency': sale.currency_id.name or '',
							'invoice_number': invoice_number,
							'po_number': sale.po_number or '',
							'log_number': sale.log_number or '',
							'term': sale.bp_term_id.name or '',
							'amount_total': amount_total,
							'deposit': sale.total_deposit,
							'point': sale.total_point*-1 if sale.total_point > 0 else sale.total_point,
							'discount': sale.total_discount*-1 if sale.total_discount > 0 else sale.total_discount,
							'ongkir': sale.total_ongkir,
							'grand_total': grand_total,
							'status': state,
							'order_state': order_state,
							'transaction_status': 1 if sale.order_state == 'terkirim' else 0,
							'order_line': order_line,
							'note': sale.note or ''
						}

		if error.get('message'):
				values = error
		else:
			values = {
				'code': 200,
				'status': True,
				'data': order_ids,
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

		if headers:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

		if body:
			user_id = body.get('user_id')
			total = body.get('total')
			payment_id = body.get('payment_id')
				
			if not total:
				error['message'] = "Total must be filled"
			
			if not payment_id:
				error['message'] = "Payment method must be filled"
			else:
				payment = env['payment.provider'].browse(int(payment_id))
				if not payment:
					error['message'] = "Payment method is not registered in the database"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					partner_id = user.partner_id
					deposit = env['bp.deposit'].create({
						'partner_id': partner_id.id,
						'total': total,
						'payment_id': payment_id,
						'date' : datetime.now()
					})
					
		if error.get('message'):
				values = error
		else:
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
			else:
				image = photo.encode()
			
			if not deposit_id:
				error['message'] = "Payment method must be filled"
			else:
				deposit = env['bp.deposit'].browse(int(deposit_id))
				if not deposit:
					error['message'] = "Payment method is not registered in the database"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					partner_id = user.partner_id
					deposit = env['bp.deposit'].search([('id', '=', deposit.id),('partner_id','=',partner_id.id)])
					deposit.write({
						'image': image
					})
					deposit.action_to_check()
					
		if error.get('message'):
				values = error
		else:
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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			start_date = post.get('start_date')
			end_date = post.get('end_date')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if start_date:
				try:
					start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S') 
				except:
					error['message'] = 'Start Date format input must be -> YYYY-MM-DD HH:MM:SS'

			if end_date:
				try:
					end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S') 
				except:
					error['message'] = 'End Date format input must be -> YYYY-MM-DD HH:MM:SS'

			if start_date and end_date:
				if start_date > end_date:
					error['message'] = 'Start Date must be smaller than End Date'

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"

		if error.get('message'):
				values = error
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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			start_date = post.get('start_date')
			end_date = post.get('end_date')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if start_date:
				try:
					start_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S') 
				except:
					error['message'] = 'Start Date format input must be -> YYYY-MM-DD HH:MM:SS'

			if end_date:
				try:
					end_date = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S') 
				except:
					error['message'] = 'End Date format input must be -> YYYY-MM-DD HH:MM:SS'

			if start_date and end_date:
				if start_date > end_date:
					error['message'] = 'Start Date must be smaller than End Date'

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"

		if error.get('message'):
				values = error
		else:
			partner_id = user.partner_id
			domain_search = [('partner_id','=', partner_id.id)]
			if start_date and not end_date:
				domain_search += [('date','>=',start_date)]
			if not start_date and end_date:
				domain_search += [('date','<=',end_date)]
			if start_date and end_date:
				domain_search += [('date','>=',start_date),('date','<=',end_date)]

			datas = member_point_obj.search(domain_search)
			data = []
			
			for member_point in datas:
				data.append({
					"id": member_point.id,
					"nama": member_point.name or '',
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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)], limit=1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					datas = payment_provider_obj.search([('code', '=', 'custom')])
					data = {
						'is_deposit': [],
						'is_credit': [],
						'is_bank': [],
						'is_cod': []
					}
					
					for payment_provider in datas:
						if payment_provider.image_128:
							image = payment_provider.image_128.decode()
						else:
							image = ''
						
						payment_data = {
							"id": payment_provider.id,
							"nama": payment_provider.name,
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

		if error.get('message'):
			values = error
		else:
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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					datas = delivery_carrier_obj.search([])
					data = []
					
					for delivery_carrier in datas:
						data.append({
							"id": delivery_carrier.id,
							"nama": delivery_carrier.name or '',
						})

		if error.get('message'):
				values = error
		else:
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
			user_id = post.get('user_id')
			job_status = post.get('job_status')
			user_token = headers.get('Authorization')
			
			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
			
			if job_status:
				job_status = json.loads(job_status)
				if type(job_status) != int:
					error['message'] = "Wrong value for job_status, use 0 or 1"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"

		if error.get('message'):
				values = error
		else:
			delivery_status = []
			if job_status:
				delivery_status = ['done']
			else:
				delivery_status = ['draft','ready','on_process','on_hold']
			
			if delivery_status:
				datas = env['stock.picking'].search([('driver_id', '=', user.id),('picking_type_code','=','outgoing'),('delivery_status','in',delivery_status)])
			else:
				datas = env['stock.picking'].search([('driver_id', '=', user.id),('picking_type_code','=','outgoing')])
			data = []
			for delivery_order in datas:
				data.append({
					"id": delivery_order.id,
					"nama": delivery_order.name,
					"customer_name": delivery_order.partner_id.name or '',
					"address": delivery_order.sale_id.full_address or delivery_order.sale_id.custom_address or '',
					"job_status" :1 if delivery_order.delivery_status == 'done' else 0,
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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			job_id = post.get('job_id')
			
			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not job_id:
				error['message'] = "Job ID must be filled"
			else:
				job = env['stock.picking'].search([('id', '=', job_id)],limit = 1)
				if not job:
					error['message'] = "Invalid jod_id"
			
			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
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
									'name': line.product_id.name,
									'variant_name': variant_name,
									'quantity': int(line.product_uom_qty),
									'price_unit': line.price_unit,
									'uom': line.product_uom.name or '',
									'subtotal': line.price_total
								})
						
						data.append({                            
							"nama": delivery_order.name,
							"customer_name": delivery_order.partner_id.name or '',
							"address_type": delivery_order.sale_id.address_type or '',
							"address": delivery_order.sale_id.full_address or delivery_order.sale_id.custom_address or '',
							"delivery_status" : delivery_order.delivery_status or '',
							"latitude" : delivery_order.partner_id.partner_latitude,
							"longitude" : delivery_order.partner_id.partner_longitude,
							"phone" : delivery_order.partner_id.phone or '',
							"delivery_name": delivery_order.sale_id.carrier_id.name or '',
							"shipping_fee": delivery_order.sale_id.total_ongkir,
							"image": image,
							"order_line": order_line,
							"total": delivery_order.sale_id.amount_total,
							"logs": {
								"driver_name": delivery_order.driver_id.name or '',
								"delivery_date" : delivery_order.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if delivery_order.scheduled_date else '',
								"delivery_date_done" : delivery_order.date_done.strftime('%Y-%m-%d %H:%M:%S') if delivery_order.date_done else ''
							}
						})

		if error.get('message'):
				values = error
		else:
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

		if headers:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

		if body:
			user_id = body.get('user_id')
			job_id = body.get('job_id')
			photo = body.get('photo')
			on_hold = body.get('on_hold')
			on_process = body.get('on_process')
			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
					
			if not job_id:
				error['message'] = "Job ID must be filled"
			else:
				job = env['stock.picking'].search([('id', '=', job_id)],limit = 1)
				if not token:
					error['message'] = "Invalid Job ID"        

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"
				else:
					datas = job
					if on_hold:
						datas.write({
							'delivery_status' : 'on_hold'
						})
					if on_process:
						datas.write({
							'delivery_status' : 'on_process'
						})
					if photo:
						image = photo.encode()
						datas.write({
							'driver_img':image
						}) 
						if datas.state not in ['cancel','done']:
							datas.button_validate()

		if error.get('message'):
				values = error
		else:
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

		if headers:
			user_token = headers.get('Authorization')

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"
		
		if body:
			user_id = body.get('user_id')
			sale_id = body.get('sale_id')
			message = body.get('message')
			# line_ids = body.get('line_ids')
					
			if not sale_id:
				error['message'] = "Sale ID must be filled"
			else:
				sale = env['sale.order'].browse(int(sale_id))
				if not sale:
					error['message'] = "Invalid Sale ID"  

			if not message:
				error['message'] = "Message must be filled"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"

		if error.get('message'):
				values = error
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

		error = {'code': 401, 'status': False}
		values = {}
		data = {}
		sale_id = post.get('sale_id',False)
		if not sale_id:
			error['message'] = "Sale ID must be filled"
		else:
			sale = env['sale.order'].search([('id','=',int(sale_id))])
			if not sale:
				error['message'] = "Invalid Sale ID"
			else:
				if not sale.invoice_ids:
					error['message'] = "Invoice not found or created" 

		if error.get('message'):
				values = error
		else:
			pdf_merger = PdfFileMerger()
			for invoice in sale.invoice_ids.filtered(lambda p: p.state == 'posted' and p.move_type == 'out_invoice'):
				pdf_content, _ = env['ir.actions.report'].sudo()._render_qweb_pdf('account.report_invoice_with_payments', [invoice.id])
				pdf_merger.append(io.BytesIO(pdf_content))

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
			user_id = post.get('user_id')
			user_token = headers.get('Authorization')
			page = int(post.get('page', 1))
			limit = int(post.get('limit', 5))
			offset = (page - 1) * limit

			if not user_token:
				error['message'] = "Token must be filled"
			else:
				token = user_obj.search([('token_api', '=', user_token)],limit = 1)
				if not token:
					error['message'] = "Invalid user_token"

			if not user_id:
				error['message'] = "User ID must be filled"
			else:
				user = user_obj.browse(int(user_id))
				if not user:
					error['message'] = "User ID is not registered in the database"

		if error.get('message'):
				values = error
		else:
			partner_id = user.partner_id
			data = []
			order_line_ids = env['sale.order.line'].search([('order_id.partner_id','=',partner_id.id),('order_id.state','in',['sale','done']),('order_id','!=',False),('product_id.detailed_type','!=','service')], limit=limit, offset=offset)
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
	
	
