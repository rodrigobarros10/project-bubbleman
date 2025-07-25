# -*- coding: utf-8 -*-

import boto3

class S3:
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

			self.client = boto3.client('s3', region_name = region, aws_access_key_id = accessKey, aws_secret_access_key = secretKey)

		except Exception as botoError:

			raise ValueError('Internal error initializating S3 Boto Client') from botoError

	def read (self, bucket = None, keyPrefix = None, decoder = 'utf-8'):
		'''
		bucket:str
		keyPrefix:str
		decoder:str - Default utf-8 - Set None to Binary files
		'''

		if not isinstance(bucket, str) or bucket == '':

			raise ValueError('Bucket must be a valid AWS S3 Bucket')

		if not isinstance(keyPrefix, str) or keyPrefix == '':

			raise ValueError('keyPrefix must be a valid path to download from S3')

		try:

			response = self.client.get_object(Bucket = bucket, Key = keyPrefix)

			if response:

				output = response['Body'].read()

				if decoder:

					output = output.decode(decoder)

				return output

			else:

				return None

		except Exception as readError:

			errorcode = readError.response['Error']['Code'] if (('Error' in readError.response) and ('Code' in readError.response['Error'])) else '***'
			
			raise ValueError('Internal error when reading %s/%s from S3. Error code: %s' % (bucket, keyPrefix, errorcode)) from readError

	def write (self, bucket = None, payload = None, keyPrefix = None, public = False, contentType = None, contentDisposition = None):
		'''
		'''

		if not isinstance(bucket, str) or bucket == '':

			raise ValueError('Bucket must be a valid AWS S3 Bucket')

		if not payload:

			raise ValueError('Cannot write "nothing" to S3 - Please provide payload')

		if not isinstance(keyPrefix, str) or keyPrefix == '':

			raise ValueError('keyPrefix must be a valid path to write something to S3')

		if contentType and not isinstance(contentType, str):

			raise ValueError('Content-Type, if provided, must be a valid string')

		if contentDisposition and not isinstance(contentDisposition, str):

			raise ValueError('Content-Disposition, if provided, must be a valid string')

		try:

			kwargs = {
				'Body': payload,
				'Bucket': bucket,
				'Key': keyPrefix
			}

			if public == True:

				kwargs['ACL'] = 'public-read'

			if contentType:

				kwargs['ContentType'] = contentType

			if contentDisposition:

				kwargs['ContentDisposition'] = contentDisposition

			self.client.put_object(**kwargs)

			return 'https://%s.s3.amazonaws.com/%s' % (
				bucket,
				keyPrefix
			)

		except Exception as botoError:

			raise ValueError('Internal error initializating S3 Boto Client') from botoError

	def scan (self, bucket = None, keyPrefix = '', maxKeys = None):
		'''
		bucket:str
		keyPrefix:str - default: empty (root)
		'''

		if not isinstance(bucket, str) or bucket == '':

			raise ValueError('Bucket must be a valid AWS S3 Bucket')

		if keyPrefix and not isinstance(keyPrefix, str):

			raise ValueError('keyPrefix, if informed, must be a valid path inside a S3\'s bucket')

		try:

			response = self.client.list_objects_v2(Bucket = bucket, Prefix = keyPrefix, MaxKeys = maxKeys)

			output = response.get('Contents', [])

			return output

		except Exception as readError:

			raise ValueError('Internal error when listing %s%s from S3.' % (bucket, keyPrefix)) from readError

	def presignedurl (self, bucket = None, keyPrefix = None, expiration = 604800):
		'''
		bucket:str
		keyPrefix:str
		decoder:str - Default utf-8 - Set None to Binary files
		'''

		if not isinstance(bucket, str) or bucket == '':

			raise ValueError('Bucket must be a valid AWS S3 Bucket')

		if not isinstance(keyPrefix, str) or keyPrefix == '':

			raise ValueError('keyPrefix must be a valid path to download from S3')

		try:

			response = self.client.generate_presigned_url('get_object', ExpiresIn = expiration, Params = {
				'Bucket': bucket,
				'Key': keyPrefix
			})

			return response

		except Exception as generateError:

			raise ValueError('Internal error when generatin pre-signed url %s/%s from S3' % (bucket, keyPrefix)) from generateError
