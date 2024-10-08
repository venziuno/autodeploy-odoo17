# -*- coding: utf-8 -*-
from odoo import api, fields, models
import uuid
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
from io import BytesIO
# import boto3
# from minio import Minio
import base64
from datetime import datetime, timedelta
import hashlib
# import urllib.parse
import time

class ResCompany(models.Model):
	_inherit = 'res.company'

	token_api = fields.Char('Token API')
	discount_product_id = fields.Many2one('product.product','Discount Product')
	point_product_id = fields.Many2one('product.product','Point Product')
	deposit_product_id = fields.Many2one('product.product','Deposit Product')
	ongkir_product_id = fields.Many2one('product.product','Ongkir Product')
	deposit_journal_id = fields.Many2one('account.journal','Deposit Journal')

	minio_url = fields.Char('Minio URL', default='storage.dextion.com')
	minio_key_id = fields.Char('Minio Key Id', default='xQl27Qmb0JKm')
	minio_access_key = fields.Char('Minio Access Key', default='b2nT99S3piC3')
	minio_region = fields.Char('Minio Region', default='ap-southeast-3')
	minio_bucket = fields.Char('Minio Bucket', default='bestindo')

	serve_url = fields.Char('Serve Image URL')

	def create_token_api(self):
		uuid_str = str(uuid.uuid4())
		self.token_api = uuid_str

	# def upload_minio(self,url, key_id, access_key, region_name, bucket, file_name, value):
	# 	# Example for MinIO
	# 	minio_client = Minio(
	# 		url,
	# 		access_key=key_id,
	# 		secret_key=access_key,
	# 		region=region_name,
	# 		secure=True  # Set to True if using HTTPS
	# 	)
	# 	if type(value) != bytes:
	# 		value_bytes = base64.b64decode(value)
	# 	else:
	# 		value_bytes = value
	# 	value_io = BytesIO(value_bytes)
		
	# 	response = minio_client.put_object(
	# 		bucket,
	# 		file_name,
	# 		value_io,
	# 		length=len(value_bytes),
	# 		content_type='image/png'
	# 	)
	# 	url = minio_client.presigned_get_object(bucket, file_name, expires=timedelta(days=7))
	# 	return url

	# def serve_image(self, path, bucket, image_url, options=None):
	# 	if not path:
	# 		return None
	# 	if options is None:
	# 		options = {}

	# 	# Hapus parameter 's' jika ada
	# 	options.pop('s', None)
		
	# 	# Tambahkan parameter 'b' dengan nilai dari AWS_BUCKET
	# 	options['b'] = bucket

	# 	# Urutkan opsi
	# 	options = dict(sorted(options.items()))

	# 	base_url = image_url

	# 	sign_key = "v-LK4WCdhcfcc%jt*VC2cj%nVpu+xQKvLUA%H86kRVk_4bgG8&CWM#k*b_7MUJpmTc=4GFmKFp7=K%67je-skxC5vz+r#xT?62tT?Aw%FtQ4Y3gvnwHTwqhxUh89wCa_"

	# 	# Trim awal '/' dari path
	# 	path = path.lstrip('/')

	# 	# Buat signature
	# 	query_string = urllib.parse.urlencode(options)
	# 	signature = hashlib.md5(f"{sign_key}:{path}?{query_string}".encode('utf-8')).hexdigest()
		
	# 	# Tambahkan signature ke options
	# 	options['s'] = signature

	# 	# Buat URL lengkap
	# 	base_url = f"{base_url.rstrip('/')}/{path.rstrip('/')}?{urllib.parse.urlencode(options)}"
		
	# 	return base_url

# class IrAttachment(models.Model):
# 	_inherit = 'ir.attachment'

# 	image_url = fields.Char('Image URL')

# 	@api.model
# 	def create(self, vals):
# 		company = self.env.company
# 		response = False
# 		if vals.get('raw'):
# 			datas = vals.get('raw')
# 			response = company.upload_minio(company.minio_url,company.minio_key_id,company.minio_access_key,company.minio_region,company.minio_bucket,vals.get('name','-'),datas)
# 			url = company.serve_image(f"/{vals.get('name','-')}", company.minio_bucket, company.serve_url)
# 			vals['image_url'] = url		

# 		return super(IrAttachment, self).create(vals)