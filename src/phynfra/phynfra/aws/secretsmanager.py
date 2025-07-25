# -*- coding: utf-8 -*-

import boto3

class SM:
	'''
	'''

	def __init__ (self, region = None, accessKey = None, secretKey = None):
		'''
		'''

		if not isinstance(region, str) or region == '':

			raise ValueError('Region must be a valid AWS Region string')

		if not isinstance(accessKey, str) or accessKey == '':

			raise ValueError('AWS Access Key ID must be a valid AWS Access Key')

		if not isinstance(secretKey, str) or secretKey == '':

			raise ValueError('AWS Secret Access Key must be a valid AWS Secret Access Key')

		try:

			self.client = boto3.client('secretsmanager', region_name = region, aws_access_key_id = accessKey, aws_secret_access_key = secretKey)

		except Exception as botoError:

			raise ValueError('Internal error initializating S3 Boto Client') from botoError

	def read (self, secret = None):
		'''
		secret:str - The key
		'''

		if not isinstance(secret, str) or secret == '':

			raise ValueError('Secret must be a valid AWS Secrets Manager key')

		try:

			response = self.client.get_secret_value(SecretId = secret)

			if response and ('SecretString' in response):

				return response['SecretString']

			else:

				return None

		except Exception as getSecretError:

			raise ValueError('Internal error when fetching "%s" from Secrets Manager' % (secret)) from getSecretError
