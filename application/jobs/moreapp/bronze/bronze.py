import csv
import json
import pandas as pd
import boto3
from io import StringIO
from datetime import datetime
import os
import ftfy


def corrigir_caracteres_avancado(texto):
	"""Corrige caracteres mal interpretados usando ftfy e substituições específicas"""
	if pd.isna(texto):
		return texto

	texto = str(texto)
	texto = ftfy.fix_text(texto)
	correcoes = {
		'N√£o': 'Não',
		'√£': 'ã',
		'√∫': 'ú',
		'√°': 'á',
		'√≥': 'ó',
		'√©': 'é',
		'√â': 'É',
		'√ö': 'Õ',
		'√º': 'ü',
		'√§': 'ä',
		'√ß': 'ç',
		'√≠': 'í',
		'√µ': 'õ',
		'√π': 'ù',
		'√¥': 'â',
		'√®': 'è',
		'√´': 'ê',
		'√∞': 'à',
		'√±': 'ñ',
		'√≠vel': 'ível',
		'√£o': 'ão',
		'N√£o Atende': 'Não Atende',
		'Nã£o Atende': 'Não Atende',
		'N√£o se aplica': 'Não se aplica',
		'poss√≠vel': 'possível',
		'avalia√ß√£o': 'avaliação',
		'N√£o poss√≠vel avalia√ß√£o': 'Não possível avaliação'
	}

	for erro, correcao in correcoes.items():
		texto = texto.replace(erro, correcao)

	return texto


def process_json_files_to_bronze(landing_bucket, bronze_bucket, landing_prefix, bronze_prefix):
	"""
	Processa arquivos JSON do bucket de landing e salva como CSV com pipe delimiter no bucket de bronze.
	"""
	s3 = boto3.client('s3')

	try:
		landing_prefix = landing_prefix.rstrip('/') + '/'
		bronze_prefix = bronze_prefix.rstrip('/') + '/'

		print(f"Procurando arquivos em: s3://{landing_bucket}/{landing_prefix}")
		response = s3.list_objects_v2(Bucket=landing_bucket, Prefix=landing_prefix)

		if 'Contents' not in response:
			print(f"Nenhum arquivo encontrado em s3://{landing_bucket}/{landing_prefix}")
			return

		json_files = [obj['Key'] for obj in response['Contents']
					  if obj['Key'].endswith('.json') and obj['Size'] > 0]

		if not json_files:
			print(f"Nenhum arquivo JSON encontrado em s3://{landing_bucket}/{landing_prefix}")
			return

		print(f"Encontrados {len(json_files)} arquivos JSON para processar:")
		for f in json_files:
			print(f" - {f}")

		for file_key in json_files:
			try:
				print(f"\nProcessando: {file_key}")
				file_name = os.path.basename(file_key)
				form_name = os.path.splitext(file_name)[0]
				form_bronze_prefix = f"{bronze_prefix}{form_name}/"

				obj = s3.get_object(Bucket=landing_bucket, Key=file_key)
				file_content = obj['Body'].read().decode('windows-1252')
				data = json.loads(file_content)

				if isinstance(data, list):
					df = pd.json_normalize(data)
				else:
					df = pd.json_normalize([data])

				df.columns = [col.replace('.', '_') for col in df.columns]

				for col in df.select_dtypes(include=['object']).columns:
					df[col] = df[col].apply(corrigir_caracteres_avancado)

				df['_processing_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

				csv_buffer = StringIO()
				df.to_csv(
					csv_buffer,
					index=False,
					sep='|',
					encoding='windows-1252',
					quoting=csv.QUOTE_NONE,
					escapechar='\\'
				)

				timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
				output_filename = f"{form_name}.csv"
				output_key = f"{form_bronze_prefix}{output_filename}"

				s3.put_object(
					Bucket=bronze_bucket,
					Key=output_key,
					Body=csv_buffer.getvalue().encode('windows-1252')
				)

				print(f"Arquivo salvo com sucesso em: s3://{bronze_bucket}/{output_key}")
				print(f"Total de registros processados: {len(df)}")

			except Exception as e:
				print(f"Erro ao processar {file_key}: {str(e)}")
				continue

	except Exception as e:
		print(f"Erro no processamento: {str(e)}")


if __name__ == "__main__":
	LANDING_BUCKET = "dev-houer-us-east-1-landing-zone"
	BRONZE_BUCKET = "dev-houer-us-east-1-bronze-zone"
	LANDING_PREFIX = "project-bubbleman/moreapp/submissions/"
	BRONZE_PREFIX = "project-bubbleman/moreapp/submissions/"

	process_json_files_to_bronze(
		landing_bucket=LANDING_BUCKET,
		bronze_bucket=BRONZE_BUCKET,
		landing_prefix=LANDING_PREFIX,
		bronze_prefix=BRONZE_PREFIX
	)
