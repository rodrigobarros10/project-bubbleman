# -*- coding: utf-8 -*-

import sys
import os
import re
import traceback
import json

from .logger import log
from dotenv import dotenv_values, load_dotenv
from importlib import import_module

REGEX_MODULE = r'[0-9a-zA-Z_]+(\.[0-9a-zA-Z_]+)*'

def run (configuration = None, module = None):
	'''
	Imports a module dynamically and run its function
	configuration:dict - python-dotenv to dict
	module:str - full module path (. separated)
	'''

	modulepath = configuration['MODULE'] if 'MODULE' in configuration else module

	if not modulepath:

		raise ValueError('MODULE is not present in configuration (.env) neither --module was provided!')

	if re.fullmatch(REGEX_MODULE, modulepath):

		split = modulepath.split('.')

		packageModule = '.'.join(split[:-1])

		functionName = split[-1]

		module = None

		try:

			module = import_module(packageModule)

		except Exception as error:

			raise error

		if hasattr(module, functionName):

			function = getattr(module, functionName)

			if callable(function):

				try:

					function(configuration)

					return {'message': '%s executed successfully' % (modulepath), 'exitcode': 0}

				except Exception as error:

					raise error

			else:

				raise ValueError('%s is not a callable function' % (modulepath))

		else:

			raise ValueError('%s is not present in %s' % (functionName, packageModule))

	else:

		raise ValueError('%s is not a valid path to package.module.function' % modulepath)

def create (configuration = None, destination = None):
	'''
	Creates a whole tree of directory for medallion architecture
	configuration:dict - python-dotenv to dict
	destination:str - target full path
	'''

	return {'message': 'NOT IMPLEMENTED', 'exitcode': 1}

	#target = configuration['DESTINATION'] if 'DESTINATION' in configuration else destination

	#if not target:

		#raise ValueError('DESTINATION is not present in configuration (.env) neither --destination was provided!')

	#elif os.path.exists(target):

		#try:

			#os.makedirs(target, exist_ok = True)

			#return {'message': '%s executed successfully' % (modulepath), 'exitcode': 0}

		#except Exception as error:

			#raise error

	#else:

		#raise ValueError('Provided destination "%s" does not exist. Please, create the root dir of the application')

def transform (configuration = None, source = None, target = None):
	'''
	'''

	return {'message': 'NOT IMPLEMENTED', 'exitcode': 1}

if __name__ == '__main__':

	import argparse

	parser = argparse.ArgumentParser()

	parser.add_argument('--command', type = str, required = True, choices=['run', 'create', 'transform'], help = 'Command is required to run phynfra in command line')
	parser.add_argument('--configuration', type = str, required = False, help = 'Configuration must be a valid path for a .env file')
	parser.add_argument('--debug', type = int, required = False, help = 'Prints all configurable dependencies and variables concerning phynfra')

	# (Override) Extra args for --command run
	parser.add_argument('--module', type = str, required = False)
	
	# (Override) Extra args for --command create
	parser.add_argument('--destination', type = str, required = False)

	arguments = parser.parse_args()

	configuration = None

	if arguments.configuration and os.path.exists(arguments.configuration):

		configuration = dotenv_values(arguments.configuration)

		load_dotenv(arguments.configuration)

		log('Executing with data from %s' % arguments.configuration, 'INFO')

	else:

		configuration = dict(os.environ)

		log('Executing with data from environment variables', 'INFO')

	if arguments.command == 'run':

		# DEBUG 

		if arguments.debug == 1:

			log(json.dumps(configuration, indent = '\t', ensure_ascii = False), 'DEBUG')

		try:

			output = run(configuration = configuration, module = arguments.module)

			log(output['message'], 'INFO')

			sys.exit(output['exitcode'])

		except Exception as error:

			trace = traceback.format_exc()

			log('Exception when running a module\'s function. Follow the traceback:\n%s' % trace, 'ERROR')

			sys.exit(1)

	elif arguments.command == 'create':

		output = create(configuration = configuration, destination = arguments.destination)

		log(output['message'], 'INFO')

		sys.exit(output['exitcode'])

	elif arguments.command == 'transform':

		output = transform(configuration = configuration, source = arguments.source, target = arguments.target)

		log(output['message'], 'INFO')

		sys.exit(output['exitcode'])
