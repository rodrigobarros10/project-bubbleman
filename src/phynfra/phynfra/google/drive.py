# -*- coding: utf-8 -*-

from phynfra.atomic.http import Fetcher
from phynfra.atomic.calendar import now, difference

from datetime import timedelta
from urllib.parse import urlencode, quote

import base64
import urllib.parse
import jwt
import json
import os
import random

class Drive ():
	'''
	All methods raise Exception when some error, exception of business logic fails
	'https://www.googleapis.com/auth/drive',
	'https://www.googleapis.com/auth/drive.file',
	'https://www.googleapis.com/auth/drive.readonly',
	'https://www.googleapis.com/auth/drive.metadata.readonly'
	'''

	def __init__ (self, accessToken = None):
		'''
		accessToken:str
		'''

		self.accessToken = accessToken

	def fetchOrCreatePathInSharedDrive (self, root = None, fullpath = None):
		'''
		root:str - Shared Drive ID (https://drive.google.com/drive/u/2/folders/SHAREDDRIVEID)
		fullpath:str - a/b/c
		'''

		if not root or not fullpath:

			raise NameError('Root or fullpath is empty. They are required!')

		if fullpath.startswith('/'):

			raise ValueError('Fullpath cannnot starts with /!')

		if fullpath.endswith('/'):

			raise ValueError('Fullpath cannnot ends with /!')

		directories = fullpath.split('/')

		directories.reverse()

		parentId = root

		directory = None

		while True:

			if len(directories) == 0:

				return parentId

			directory = directories.pop()

			if not directory:

				return parentId

			try:

				queryParameters = {
					'corpora': 'drive',
					'fields': 'nextPageToken, files(id, name)',
					'includeItemsFromAllDrives': 'true',
					'supportsAllDrives': 'true',
					'useDomainAdminAccess': 'true',
					'pageSize': 1000,
					'driveId': root,
					'q': "'%s' in parents and name = '%s' and mimeType = 'application/vnd.google-apps.folder'" % (
						parentId,
						directory
					)
				}

				f = Fetcher('https://www.googleapis.com/drive/v3/files?%s' % urlencode(queryParameters, doseq = True, quote_via = quote), False)

				response = f.fetch('GET', headers = {
					'Authorization': 'Bearer %s' % self.accessToken,
					'Content-Type': 'application/json'
				})

				if response['ok'] == False:

					raise RuntimeError('Fail to GET response from Google Drive API when listing files: %s' % response['response'])

				queryResponse = json.loads(response['response'])

				files = queryResponse['files']

				if 'files' in queryResponse and len(queryResponse['files']) == 1:
					
					parentId = queryResponse['files'][0]['id']

				else:

					try:

						f1 = Fetcher('https://www.googleapis.com/drive/v3/files?supportsAllDrives=true', False)

						response1 = f1.fetch('POST', payload = json.dumps({
							'description': directory,
							'mimeType': 'application/vnd.google-apps.folder',
							'name': directory,
							'parents': [
								parentId
							]
						}, ensure_ascii = False), headers = {
							'Authorization': 'Bearer %s' % self.accessToken,
							'Content-Type': 'application/json'
						})

						folderResponse = json.loads(response1['response'])

						parentId = folderResponse['id']

					except Exception as createError:

						raise RuntimeError('POST to Google Drive API for %s creation raised error' % directory) from createError

			except Exception as processError:

				raise RuntimeError("Internal error when fetching of creating path in Shared Drive") from processError

	def uploadFileToSharedDrive (self, bufferedFile = None, mimetype = None, metadata = None):
		'''
		metadata:dict - description, name, parents[]
		'''

		try:

			boundary = f"{hex(int(random.random() * 1e17))[2:].upper()}=="

			data = []

			data.append(f"--{boundary}")
			data.append('Content-Type: application/json; charset=UTF-8')
			data.append('')
			data.append(json.dumps(metadata, separators = (',', ':'), ensure_ascii = False))
			data.append(f"--{boundary}")
			data.append('Content-Type: %s' % mimetype)
			data.append('Content-Transfer-Encoding: base64')
			data.append('')
			data.append(base64.b64encode(bufferedFile).decode('utf-8'))
			data.append(f"--{boundary}--")
			data.append('')

			body = '\r\n'.join(data)

			f = Fetcher('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&supportsAllDrives=true&fields=id,webViewLink,hasThumbnail,thumbnailLink,name,kind,parents', False)

			response = f.fetch('POST', payload = body, headers = {
				'Authorization': 'Bearer %s' % self.accessToken,
				'Content-Type': 'multipart/related; boundary="%s"' % boundary,
				'Content-Length': str(len(body))
			})

			if response['ok'] == True:

				return json.loads(response['response'])

			else:

				raise RuntimeError('Error uploading file to Google Drive: %s' % response['response'])

		except Exception as uploadError:

			raise RuntimeError("Exception when upload file to Google Drive") from uploadError

	def unloadFileFromSharedDrive (self, fileId = None):
		'''
		PENDING
		'''

		try:

			f = Fetcher('https://www.googleapis.com/drive/v3/files/%s?supportsAllDrives=true' % quote(fileId, safe = ''), False)

			response = f.fetch('DELETE', headers = {
				'Authorization': 'Bearer %s' % self.accessToken
			})

			if response['ok'] == True:

				output = json.loads(response['response'])
				
				return output

			else:

				raise RuntimeError("Error deleting file form Google Drive: %s" % response['response'])

		except Exception as deleteError:

			raise RuntimeError("Exception when deleting a file from Google Drive") from deleteError

	def downloadFileFromSharedDrive (self, fileId, fullpath = None):
		'''
		filename:str if fullpath (filename from google drive)
		binary:bytes if not fullpath
		'''

		f = None

		try:

			f = Fetcher('https://www.googleapis.com/drive/v3/files/%s?supportsAllDrives=true' % fileId, False)

			dataResponse = f.fetch('GET', headers = {
				'Authorization': 'Bearer %s' % self.accessToken,
				'Content-Type': 'application/json'
			})

			if dataResponse['ok'] == True:

				file = json.loads(dataResponse['response'])

				f.update(url = 'https://www.googleapis.com/drive/v3/files/%s?alt=media&supportsAllDrives=true' % fileId)

				binaryResponse = f.fetch('GET', stream = True, headers = {
					'Authorization': 'Bearer %s' % self.accessToken,
					'Content-Type': 'application/json'
				})

				if binaryResponse['ok'] == True:

					if fullpath != None and isinstance(fullpath, str):

						if os.path.exists(fullpath):

							os.unlink(fullpath)

						handler = open(fullpath, 'wb')

						handler.write(binaryResponse['response'])

						handler.close()

						jsonfullpath = '%s.json' % fullpath

						if os.path.exists(jsonfullpath):

							os.unlink(jsonfullpath)

						handler = open(jsonfullpath, 'w')

						handler.write(dataResponse['response'])

						handler.close()

						return file['name']

					else:

						return binaryResponse['response']

				else:

					raise RuntimeError("Fail to download file from Google Drive")

			else:

				raise RuntimeError("Error fetching metada from file form Google Drive: %s" % response['response'])

		except Exception as fetchError:

			raise RuntimeError("Exception when fetching metadata from a file from Google Drive") from fetchError

	def copyFileInSharedDrive (self, fileId, target):
		'''
		'''

		try:

			parameters = {
				'parents': [
					target
				]
			}

			f = Fetcher('https://www.googleapis.com/drive/v3/files/%s/copy?supportsAllDrives=true' % quote(fileId, safe = ''), False)

			response = f.fetch('POST', payload = json.dumps(parameters, separators = (',', ':'), ensure_ascii = False), headers = {
				'Authorization': 'Bearer %s' % self.accessToken,
				'Content-Type': 'application/json'
			})

			if response['ok'] == True:

				return json.loads(response['response'])

			else:

				raise RuntimeError("Error copying file form Google Drive: %s" % response['response'])

		except Exception as copyingError:

			raise RuntimeError("Exception when copying a file from Google Drive") from copyingError

	def moveFileInSharedDrive (self, fileId, removeParents, addParents):
		'''
		fileId:str
		removeParents:[str]
		addParents:[str]
		'''

		try:

			parameters = {
				'supportsAllDrives': 'true',
				'addParents': ','.join(addParents),
				'removeParents': ','.join(removeParents)
			}

			f = Fetcher('https://www.googleapis.com/drive/v3/files/%s?%s' % (fileId, urlencode(parameters, doseq = True, quote_via = quote)), False)

			response = f.fetch('PATCH', headers = {
				'Authorization': 'Bearer %s' % self.accessToken,
				'Content-Type': 'application/json'
			})

			if response['ok'] == True:

				return json.loads(response['response'])

			else:

				raise RuntimeError("Error moving file form Google Drive: %s" % response['response'])

		except Exception as movingError:

			raise RuntimeError("Exception when moving a file from Google Drive") from movingError

	def recursivePlainListFilesByPageToken (self, driveId = None, parents = None, pageToken = None, output = None):
		'''
		output must be an array, outside the first call defined
		'''

		if pageToken == None:

			raise ValueError('pageToken cannot be none or empty')

		parameters = {
			'fields': 'nextPageToken, files(id, name, mimeType, parents)',
			'includeItemsFromAllDrives': 'true',
			'supportsAllDrives': 'true',
			'useDomainAdminAccess': 'true',
			'pageSize': 1000,
			'q': 'trashed = false'
		}

		if driveId:

			parameters['corpora'] = 'drive'
			parameters['driveId'] = driveId

		if pageToken:

			parameters['pageToken'] = pageToken

		if parents and len(parents) > 0:

			parameters['q'] += " and '%s' in parents" % parents
		
		f = Fetcher('https://www.googleapis.com/drive/v3/files?%s' % urlencode(parameters, doseq = True, quote_via = quote), False)

		response = f.fetch('GET', headers = {
			'Authorization': 'Bearer %s' % self.accessToken,
			'Content-type': 'application/json'
		})
		
		if response['ok'] == True:

			filesResponse = json.loads(response['response'])

			if 'files' in filesResponse and len(filesResponse['files']) > 0:

				for file in filesResponse['files']:

					if file['mimeType'] == 'application/vnd.google-apps.folder':

						file['type'] = 'folder'

					else:

						file['type'] = 'file'

					output.append(file)

				if 'nextPageToken' in filesResponse and filesResponse['nextPageToken']:

					self.recursivePlainListFilesByPageToken(driveId, parents, filesResponse['nextPageToken'], output)		

	def recursiveDeepListFilesByPageToken (self, driveId = None, parents = None, pageToken = None, output = None):
		'''
		output must be an array, outside the first call defined
		'''

		if pageToken == None:

			raise ValueError('pageToken cannot be none or empty')

		parameters = {
			'fields': 'nextPageToken, files(id, name, mimeType, parents)',
			'includeItemsFromAllDrives': 'true',
			'supportsAllDrives': 'true',
			'useDomainAdminAccess': 'true',
			'pageSize': 1000,
			'q': 'trashed = false'
		}

		if driveId:

			parameters['corpora'] = 'drive'
			parameters['driveId'] = driveId

		if pageToken:

			parameters['pageToken'] = pageToken

		if parents and len(parents) > 0:

			parameters['q'] += " and '%s' in parents" % parents
		
		f = Fetcher('https://www.googleapis.com/drive/v3/files?%s' % urlencode(parameters, doseq = True, quote_via = quote), False)

		response = f.fetch('GET', headers = {
			'Authorization': 'Bearer %s' % self.accessToken,
			'Content-type': 'application/json'
		})
		
		if response['ok'] == True:

			filesResponse = json.loads(response['response'])

			if 'files' in filesResponse and len(filesResponse['files']) > 0:

				for file in filesResponse['files']:

					if file['mimeType'] == 'application/vnd.google-apps.folder':

						self.recursiveDeepListFilesByPageToken(driveId, file['id'], False, output)

					else:

						output.append(file)

				if 'nextPageToken' in filesResponse and filesResponse['nextPageToken']:

					self.recursiveDeepListFilesByPageToken(driveId, parents, filesResponse['nextPageToken'], output)

	def recursiveDeepTreeListFilesByPageToken (self, driveId = None, parents = None, pageToken = None, output = None):
		'''
		output must be a dict, outside the first call defined
		output = {'files': []}
		'''

		if pageToken == None:

			raise ValueError('pageToken cannot be none or empty')

		parameters = {
			'fields': 'nextPageToken, files(id, name, mimeType, parents)',
			'includeItemsFromAllDrives': 'true',
			'supportsAllDrives': 'true',
			'useDomainAdminAccess': 'true',
			'pageSize': 1000,
			'q': 'trashed = false'
		}

		if driveId:

			parameters['corpora'] = 'drive'
			parameters['driveId'] = driveId

		if pageToken:

			parameters['pageToken'] = pageToken

		if parents and len(parents) > 0:

			parameters['q'] += " and '%s' in parents" % parents
		
		f = Fetcher('https://www.googleapis.com/drive/v3/files?%s' % urlencode(parameters, doseq = True, quote_via = quote), False)

		response = f.fetch('GET', headers = {
			'Authorization': 'Bearer %s' % self.accessToken,
			'Content-type': 'application/json'
		})
		
		if response['ok'] == True:

			filesResponse = json.loads(response['response'])

			if 'files' in filesResponse and len(filesResponse['files']) > 0:

				for file in filesResponse['files']:

					if file['mimeType'] == 'application/vnd.google-apps.folder':

						output[file['name']] = {
							'files': []
						}

						self.recursiveDeepTreeListFilesByPageToken(driveId, file['id'], False, output[file['name']])

					else:

						output['files'].append(file)

				if 'nextPageToken' in filesResponse and filesResponse['nextPageToken']:

					self.recursiveDeepTreeListFilesByPageToken(driveId, parents, filesResponse['nextPageToken'], output)
