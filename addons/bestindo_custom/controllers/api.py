from odoo import http
from odoo.http import request, Response
import json
import odoo
from odoo.exceptions import AccessDenied
import uuid
import base64

class BestindoAPI(http.Controller):
    @http.route('/bp/login', methods=['POST'], type='http', auth="public", csrf=False, website=True)
    def bp_login(self, **post):
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
        error = {'code': 401}
        company = user_obj.browse(uid).company_id

        if body:
            username = body.get('username')
            password = body.get('password')
            token = body.get('token')
            registration_id = body.get('registration_id')

            if not token:
                error['message'] = "Token must be filled"
            else:
                if token != company.token_api:
                    error['message'] = "Invalid token"

            if not username:
                error['message'] = "Username must be filled"
            if not password:
                error['message'] = "Password must be filled"
            if not registration_id:
                error['message'] = "Registration ID must be filled"

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
                if registration_id != user.partner_id.registration_id:
                    user.partner_id.write({'registration_id': registration_id})
                values = {
                    'code': 200,
                    'user_id': user.id,
                    'name': user.name,
                    'message': "You are successfully login"
                }
        else:
            error['message'] = "Empty params"
            values = error

        headers = {'Access-Control-Allow-Origin': '*'}
        return Response(json.dumps(values), headers=headers)

    @http.route('/bp/logout', methods=['POST'], type='http', auth="public", csrf=False, website=True)
    def bp_logout(self, **post):
        cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
        request.update_env(user=odoo.SUPERUSER_ID)
        env = request.env
        body = request.httprequest.data                
        body = json.loads(body)

        error = {'code': 401}
        user_obj = env['res.users']
        company = user_obj.browse(uid).company_id

        values = {}
        if type(body) == str:
            body = json.loads(body)

        if body:
            token = body.get('token')
            if not token:
                error['message'] = "Token must be filled"
            else:
                if token != company.token_api:
                    error['message'] = "Invalid token"

        if error.get('message'):
                values = error
        else:
            request.session.logout()
            values = {
                'code': 200,
                'message': "You are successfully logout",
            }
        headers = {'Access-Control-Allow-Origin': '*'}
        return Response(json.dumps(values), headers=headers)

    @http.route('/bp/reset-password', methods=['POST'], type='http', auth="public", csrf=False, website=True)
    def bp_reset_password(self, **post):
        cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
        request.update_env(user=odoo.SUPERUSER_ID)
        env = request.env
        body = request.httprequest.data                
        body = json.loads(body)
        user_obj = env['res.users']

        error = {'code': 401}
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
                'message': "Success, please check your email if you want to reset the password",
            }
        headers = {'Access-Control-Allow-Origin': '*'}
        return Response(json.dumps(values), headers=headers)

    @http.route('/bp/get-profile', methods=['GET'], type='http', auth="public", csrf=False, website=True)
    def bp_get_profile(self, **post):
        cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
        request.update_env(user=odoo.SUPERUSER_ID)
        env = request.env
        body = request.httprequest.data                
        body = json.loads(body)
        user_obj = env['res.users']

        error = {'code': 401}
        values = {}
        data = {}
        user_obj = env['res.users']
        partner_obj = env['res.partner']

        company = user_obj.browse(uid).company_id
        if type(body) == str:
            body = json.loads(body)

        if body:
            user_id = body.get('user_id')
            token = body.get('token')
            if not token:
                error['message'] = "Token must be filled"
            else:
                if token != company.token_api:
                    error['message'] = "Invalid token"

            if not user_id:
                error['message'] = "User ID must be filled"
            else:
                user = user_obj.browse(int(user_id))
                if not user:
                    error['message'] = "User ID is not registered in the database"
                else:
                    partner = user.partner_id
                    data = {
                        'name': partner.name or '',
                        'address': (str(partner.street or '') + str(partner.street2 or '') + str(partner.city or '') + str(partner.state_id.name or '') + str(partner.zip or '')) or '',
                        'phone': partner.phone or '',
                        'email': partner.email or '',
                        'photo': base64.b64encode(partner.image_1920 or '').decode('utf-8') or '',
                        'total_deposit': partner.total_deposit,
                        'loyalty_point': partner.loyalty_point
                    }

        if error.get('message'):
                values = error
        else:
            values = {
                'code': 200,
                'data': data
            }
        headers = {'Access-Control-Allow-Origin': '*'}
        return Response(json.dumps(values), headers=headers)

    @http.route('/bp/update-profile', methods=['POST'], type='http', auth="public", csrf=False, website=True)
    def bp_update_profile(self, **post):
        cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
        request.update_env(user=odoo.SUPERUSER_ID)
        env = request.env
        body = request.httprequest.data                
        body = json.loads(body)
        user_obj = env['res.users']

        error = {'code': 401}
        values = {}
        data = {}
        user_obj = env['res.users']
        partner_obj = env['res.partner']

        company = user_obj.browse(uid).company_id
        if type(body) == str:
            body = json.loads(body)

        if body:
            user_id = body.get('user_id')
            token = body.get('token')
            if not token:
                error['message'] = "Token must be filled"
            else:
                if token != company.token_api:
                    error['message'] = "Invalid token"

            if not user_id:
                error['message'] = "User ID must be filled"
            else:
                user = user_obj.browse(int(user_id))
                if not user:
                    error['message'] = "User ID is not registered in the database"
                else:
                    partner = user.partner_id
                    data = {
                        'name': partner.name or '',
                        'address': (str(partner.street or '') + str(partner.street2 or '') + str(partner.city or '') + str(partner.state_id.name or '') + str(partner.zip or '')) or '',
                        'phone': partner.phone or '',
                        'email': partner.email or '',
                        'photo': base64.b64encode(partner.image_1920 or '').decode('utf-8') or '',
                        'total_deposit': partner.total_deposit,
                        'loyalty_point': partner.loyalty_point
                    }

        if error.get('message'):
                values = error
        else:
            values = {
                'code': 200,
                'data': data
            }
        headers = {'Access-Control-Allow-Origin': '*'}
        return Response(json.dumps(values), headers=headers)

    @http.route('/bp/get-order', methods=['GET'], type='http', auth="public", csrf=False, website=True)
    def bp_get_order(self, **post):
        cr, uid, pool, context = request.cr, odoo.SUPERUSER_ID, request.registry, request.context
        request.update_env(user=odoo.SUPERUSER_ID)
        env = request.env
        body = request.httprequest.data                
        body = json.loads(body)
        user_obj = env['res.users']

        error = {'code': 401}
        values = {}
        data = {}
        user_obj = env['res.users']
        partner_obj = env['res.partner']
        sale_obj = env['sale.order']

        company = user_obj.browse(uid).company_id
        if type(body) == str:
            body = json.loads(body)

        if body:
            user_id = body.get('user_id')
            token = body.get('token')
            if not token:
                error['message'] = "Token must be filled"
            else:
                if token != company.token_api:
                    error['message'] = "Invalid token"

            if not user_id:
                error['message'] = "User ID must be filled"
            else:
                user = user_obj.browse(int(user_id))
                if not user:
                    error['message'] = "User ID is not registered in the database"
                else:
                    partner = user.partner_id
                    order_ids = []
                    sale_ids = sale_obj.search([('partner_id','=',partner.id)])
                    for sale in sale_ids:
                        order_line = []
                        if sale.state == 'draft':
                            state = 'Draft'
                        if sale.state == 'sent':
                            state = 'Waiting Payment'
                        if sale.state == 'sale':
                            state = 'Done'
                        if sale.state == 'cancel':
                            state = 'Cancel'

                        for line in sale.order_line:
                            order_line.append({
                                'product': line.product_id.name,
                                'quantity': line.product_uom_qty,
                                'total': line.price_subtotal
                            })
                        order_ids.append({
                            'name': sale.name,
                            'date_order': sale.date_order.strftime('%Y-%m-%d %H:%M:%S'),
                            'amount_total': sale.amount_total,
                            'status': state,
                            'order_line': order_line
                        })

        if error.get('message'):
                values = error
        else:
            values = {
                'code': 200,
                'data': order_ids
            }
        headers = {'Access-Control-Allow-Origin': '*'}
        return Response(json.dumps(values), headers=headers)