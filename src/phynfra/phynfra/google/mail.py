# -*- coding: utf-8 -*-

from phynfra.atomic.http import Fetcher

from urllib.parse import urlencode, quote

import base64
import urllib.parse
import jwt
import json
import os
import random

class Mail ():
	'''
	All methods raise Exception when some error, exception of business logic fails
	'https://mail.google.com/',
	'https://www.googleapis.com/auth/gmail.modify',
	'https://www.googleapis.com/auth/gmail.compose',
	'https://www.googleapis.com/auth/gmail.send',
	'''

	def __init__ (self, accessToken = None):
		'''
		accessToken:str
		'''

		self.accessToken = accessToken


	def send (self, to = None, reply = None, subject = None, body = None):
		'''
		'''

		try:

			encodedSubject = "=?utf-8?B?%s?=" % base64.b64encode(subject.encode('utf-8')).decode('utf-8')

			rfc2822 = "To: %s\r\nSubject: %s\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n%s" % (
				to,
				encodedSubject,
				body
			)

			payload = {
				"raw": base64.urlsafe_b64encode(rfc2822.encode('utf-8')).decode('utf-8')
			}

			f = Fetcher('https://gmail.googleapis.com/gmail/v1/users/me/messages/send', False)

			response = f.fetch('POST', payload = json.dumps(payload, separators = (',', ':'), ensure_ascii = False), headers = {
				'Authorization': 'Bearer %s' % self.accessToken,
				'Content-Type': 'application/json'
			})

			if response['ok'] == True:

				return json.loads(response['response'])

			else:

				raise RuntimeError('Error sending plain e-mail: %s' % response['response'])

		except Exception as sendError:

				raise RuntimeError("Exception when sending e-mail") from sendError


