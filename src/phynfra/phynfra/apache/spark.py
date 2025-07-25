# -*- coding: utf-8 -*-

import os

from pyspark.sql import SparkSession

from pandas import DataFrame as PandasDataFrame
from pyspark.sql.dataframe import DataFrame as SparkDataFrame
from pyspark.sql.types import ArrayType, DoubleType, FloatType, IntegerType, LongType, StringType, StructField, StructType, TimestampType

from urllib.parse import urlparse

class Spark ():
	'''
	Spark Class
	Manages SparkSession
	'''
	
	def __init__ (self, application, configuration = None, level = 'WARN'):
		'''
		Initialize a SparkSession
		application:str - Application name
		configuration:dict - From .env configuration
		level:str - DEBUG Level - WARN Default
		'''

		if not application:

			raise ValueError('Spark Application Name is required!')
		
		try:

			builder = SparkSession.builder.appName(application)

			if isinstance(configuration, dict):

				for (key, value) in configuration.items():

					builder.config(key, value)

			else:

				builder = builder.master('local[*]')

			self.spark = builder.getOrCreate()

			self.spark.sparkContext.setLogLevel(level)

		except Exception as error:

			raise error

	def get (self):
		'''
		Get spark session
		'''

		return self.spark

	def stop (self):
		'''
		Stop Spark Session
		'''

		self.spark.stop()

class DataFramer ():
	'''
	Encapsulates Operations of/to a SparkDataFrame
	'''

	def __init__ (self, spark):
		'''
		spark:Spark - A phynfra spark manager to retrieve session
		'''

		if isinstance(spark, Spark):

			self._spark = spark.get()

			self.dataframe = None

		else:

			raise ValueError('Cannot create a DataFrame without Spark Session (spark argument)')

	def get (self):
		'''
		Returns the current dataframe
		'''

		return self.dataframe

	def create (self, schema):
		'''
		Create an empty dataframe by a schema
		'''

		# TODO: handle schema

		self.dataframe = self._spark.createDataFrame([], schema = schema)

		return self

	def append (self, data):
		'''
		'''

		if (not data) or (len(data) == 0):

			raise ValueError('To append data to a DataFrame it should be a list of data according to DataFrame schema')

		if not self.dataframe:

			raise ValueError('DataFramer\'s DataFrame does not exists. Create it first.')

		new = self._spark.createDataFrame(data, schema = self.dataframe.schema)

		self.dataframe = self.dataframe.union(new)

		del new

		return self

	def read (self, fullpath, arguments):
		'''
		Build-in is a capacity of Spark itself
		fullpath:str* - URI
		arguments:dict
		'''

		if not fullpath:

			raise ValueError('Cannot read to a DataFrame an empty or None fullpath')

		try:

			parsed = urlparse(fullpath)

			basename = os.path.basename(parsed.path)

			filename, extension = os.path.splitext(basename)

			if not arguments:

				arguments = {
					'format': extension[1:]
				}

			elif 'format' not in arguments:

				arguments['format'] = extension[1:]

			self.dataframe = self.loadDataFrameNative(fullpath, arguments)

			return self

		except Exception as error:

			raise error

	def write (self, fullpath, arguments, dataframe = None, overwrite = True):
		'''
		Build-in is a capacity of Spark itself
		fullpath:str* - URI
		arguments:dict
		dataframe:SparkDataFrame - Another DF to be written
		'''

		if not fullpath:

			raise ValueError('Cannot write to a destination without a fullpath')

		try:

			parsed = urlparse(fullpath)

			basename = os.path.basename(parsed.path)

			filename, extension = os.path.splitext(basename)

			if not arguments:

				arguments = {
					'format': extension[1:]
				}

			elif 'format' not in arguments:

				arguments['format'] = extension[1:]

			outer = dataframe if isinstance(dataframe, SparkDataFrame) else self.dataframe

			if overwrite == True:

				outer.write.mode('overwrite').save(fullpath, **arguments)

			else:

				outer.write.save(fullpath, **arguments)

			return self

		except Exception as error:

			raise error

	def loadDataFrameNative (self, fullpath, arguments):
		'''
		'''

		return self._spark.read.load(fullpath, **arguments)

	def toPandas (self):
		'''
		'''

		if self.dataframe:

			self.dataframe = self.dataframe.toPandas()

		else:

			raise ValueError('Cannot convert to Pandas\' DataFrame something that does not exist')

		return self

	def fromPandas (self, dataframe = None):
		'''
		'''

		reference = dataframe if dataframe else self.dataframe

		if reference and isinstance(reference, PandasDataFrame):

			self.dataframe = self._spark.createDataFrame(reference)

		else:

			raise ValueError('DataFrame must be an instance of pandas.DataFrame to be converted')

		return self

	def toList (self):

		if self.dataframe:

			if isinstance(self.dataframe, SparkDataFrame):

				return self.dataframe.collect()

			elif isinstance(instance, PandasDataFrame):

				return self.dataframe.values.tolist()

			else:

				return []

		else:

			raise ValueError('Cannot convert to Python List something that does not exist')

		return self

	# get_df_latest_batch :: https://github.com/houertecnologia/project-turboman/blob/dev/processing/app/commons/helpers/spark_utils.py
	# flatten :: https://github.com/houertecnologia/project-turboman/blob/dev/processing/app/commons/helpers/spark_utils.py
	