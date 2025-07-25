import boto3
import json
import os
from datetime import datetime
from typing import Any, Dict, List
from botocore.exceptions import NoCredentialsError, ClientError
from phynfra.atomic.http import Fetcher
import ftfy


class MoreAppToS3Processor:
	def __init__(self):
		"""
        Inicializa o processador com autenticação S3 via variáveis de ambiente
        """
		self.s3_client = None
		self.moreapp_forms = {
			"IRS - Coleta RSD - Produtividade": "66c8d998e5a2cf14ff76cdcd",
			"IRS - Coleta RSD - Veículo": "66e3337fe4bb966929ce5346",
			"IRS - Coleta RSD - Frota": "66e33424e4bb966929ce5348",
			"IRS - Coleta Seletiva": "66e335a68410676c7282034b",
			"ILU - Varrição Manual": "66e3368b8410676c72820358",
			"ILU - Produtividade": "66e43cc58410676c72820a7a",
			"Ambiental - IRS - Coleta Seletiva": "67fe71ace4ea1401e28ea185"
		}

	def authenticate_s3(self):
		"""
        Autentica no serviço S3 da AWS usando variáveis de ambiente
        """
		try:
			self.s3_client = boto3.client('s3')
			self.s3_client.list_buckets()  # Testa a conexão
			return True
		except (NoCredentialsError, ClientError) as e:
			print(f"Erro na autenticação S3: {e}")
			return False

	@staticmethod
	def safe_flatten_json(data: Any, parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
		"""Flatten JSON data safely with type checking."""
		flattened = {}
		if isinstance(data, dict):
			for key, value in data.items():
				new_key = f"{parent_key}{sep}{key}" if parent_key else key
				flattened.update(MoreAppToS3Processor.safe_flatten_json(value, new_key, sep))
		elif isinstance(data, list):
			for i, item in enumerate(data):
				flattened.update(MoreAppToS3Processor.safe_flatten_json(item, f"{parent_key}{sep}{i}", sep))
		else:
			if parent_key:
				flattened[parent_key] = data
		return flattened

	@staticmethod
	def process_and_flatten_data(data: List[Any]) -> List[Dict[str, Any]]:
		"""Process and flatten the data with proper error handling."""
		flattened_data = []
		for item in data:
			try:
				if not isinstance(item, (dict, list)):
					if isinstance(item, str):
						try:
							item = json.loads(item)
						except json.JSONDecodeError:
							continue
				flattened_item = MoreAppToS3Processor.safe_flatten_json(item)
				if flattened_item:
					flattened_data.append(flattened_item)
			except Exception as e:
				print(f"Erro ao processar item: {str(e)}")
				continue
		return flattened_data

	def save_to_s3(self, data: Dict, s3_bucket: str, s3_key: str):
		"""Salva dados diretamente no S3 sem arquivo local"""
		try:
			self.s3_client.put_object(
				Bucket=s3_bucket,
				Key=s3_key,
				Body=json.dumps(data, ensure_ascii=False).encode('windows-1252'),
				ContentType='application/json'
			)
			print(f"Upload para S3 bem-sucedido: {s3_key}")
			return True
		except Exception as s3_error:
			print(f"Erro ao enviar para S3: {str(s3_error)}")
			return False

	def process_form_data(self, form_name: str, form_id: str):
		"""Processa dados de um formulário específico"""
		headers = {
			"Content-Type": "application/json",
			"Accept": "*/*",
			"X-Api-Key": "kIQblHraCHvDC46fB2wJ8_XXWObF9D0dJW-dIU9aF2g="
		}

		payload = {
			"json": {
				"pageSize": 100,
				"sort": [{"key": "meta.registrationDate", "direction": -1}]
			}
		}

		all_data = []
		validador = 1
		page = 0

		try:
			while validador != 0:
				url = f"https://api.moreapp.com/api/v1.0/customers/163779/forms/{form_id}/submissions/filter/{page}"
				fetch = Fetcher(url=url)
				response = fetch.fetch(verb="POST", headers=headers, payload=json.dumps(payload))

				if "response" not in response:
					print(f"Resposta inesperada da API para {form_name}")
					break

				response_data = json.loads(response["response"])
				validador = len(response_data.get("elements", []))

				if validador == 0:
					break

				for element in response_data["elements"]:
					try:
						timestamp_in_seconds = element["info"]["date"] / 1000
						formatted_date = datetime.fromtimestamp(timestamp_in_seconds)
						if formatted_date >= datetime(2023, 1, 1):
							all_data.append(element)
					except (KeyError, TypeError):
						continue

				page += 1

			if not all_data:
				print(f"Nenhum dado válido encontrado para {form_name}")
				return

			flattened_data = self.process_and_flatten_data(all_data)
			if not flattened_data:
				print(f"Nenhum dado válido para {form_name} após processamento")
				return

			# Função para corrigir caracteres em strings aninhadas
			def corrigir_caracteres(obj):
				if isinstance(obj, str):
					# Primeiro aplica ftfy para correções automáticas
					texto_corrigido = ftfy.fix_text(obj)
					# Depois aplica substituições específicas
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
						texto_corrigido = texto_corrigido.replace(erro, correcao)
					return texto_corrigido
				elif isinstance(obj, dict):
					return {k: corrigir_caracteres(v) for k, v in obj.items()}
				elif isinstance(obj, list):
					return [corrigir_caracteres(v) for v in obj]
				else:
					return obj

			# Aplicar correção de caracteres em toda a estrutura de dados
			flattened_data = corrigir_caracteres(flattened_data)

			# Upload direto para S3
			timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
			s3_bucket = "dev-houer-us-east-1-landing-zone"
			s3_key = f"project-bubbleman/moreapp/submissions/{form_name}/{form_name}_{form_id}.json"

			if self.save_to_s3(flattened_data, s3_bucket, s3_key):
				print(f"Dados processados e salvos para {form_name}")

		except Exception as e:
			print(f"Erro principal ao processar {form_name}: {str(e)}")

	def run(self):
		"""Método principal para executar o processamento"""
		if not self.authenticate_s3():
			print("Falha na autenticação com S3. Processamento abortado.")
			return

		for form_name, form_id in self.moreapp_forms.items():
			print(f"Processando formulário: {form_name}")
			self.process_form_data(form_name, form_id)


if __name__ == "__main__":
	processor = MoreAppToS3Processor()
	processor.run()
