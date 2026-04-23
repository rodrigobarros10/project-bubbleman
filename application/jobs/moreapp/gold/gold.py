import pandas as pd
from dotenv import load_dotenv

from src.phynfra.phynfra.aws.s3 import S3
import os
from io import StringIO, BytesIO
import boto3

load_dotenv()
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")



project = "project-bubbleman"
moreapp_forms = {
	"irsp": "66c8d998e5a2cf14ff76cdcd",
	"irsv": "66e3337fe4bb966929ce5346",
	"irsf": "66e33424e4bb966929ce5348",
	"irss": "66e335a68410676c7282034b",
	"ilum": "66e3368b8410676c72820358",
	"ilup": "66e43cc58410676c72820a7a",
	"amb":  "67fe71ace4ea1401e28ea185",
	"irsrsd": "68af649704facf339a350ceb"
}



def scan_content_in_s3_bucket(s3_boto_client: boto3.client, content: str, moreapp_form: str) -> list:
	"""Escaneia arquivos de mídia no bucket público."""
	try:
		s3_bucket = "houer-vi-publico"
		prefix = f"{project}/moreapp/{content}/{moreapp_form}/"
		paginator = s3_boto_client.get_paginator('list_objects_v2')
		pages = paginator.paginate(Bucket=s3_bucket, Prefix=prefix)
		content_keys = []
		for page in pages:
			for obj in page.get('Contents', []):
				if f'{moreapp_form}/' in obj['Key']:
					file_name = obj['Key'].split(f'{moreapp_form}/', 1)[1]
					content_keys.append(file_name)
		return content_keys
	except Exception as e:
		print(f"Erro ao escanear o bucket público para {content}/{moreapp_form}: {e}")
		return []


def find_latest_csv_for_form(s3_boto_client: boto3.client, bucket: str, form_name: str) -> str:
	"""Encontra o CSV mais recente para um formulário."""
	form_prefix = f"{project}/moreapp/submissions/{form_name}/"
	try:
		print(f"Buscando arquivos na pasta: s3://{bucket}/{form_prefix}")
		response = s3_boto_client.list_objects_v2(Bucket=bucket, Prefix=form_prefix)
		if 'Contents' not in response:
			print("Nenhum arquivo encontrado na pasta.")
			return None
		csv_files = [obj for obj in response['Contents'] if obj['Key'].lower().endswith('.csv')]
		if not csv_files:
			print("Nenhum arquivo .csv encontrado na pasta.")
			return None
		sorted_files = sorted(csv_files, key=lambda obj: obj['LastModified'], reverse=True)
		latest_file_key = sorted_files[0]['Key']
		print(f"Arquivo CSV mais recente encontrado: {latest_file_key}")
		return latest_file_key
	except Exception as e:
		print(f"Erro ao buscar arquivos na S3: {e}")
		return None


def generate_final_df(s3_phynfra_client: S3, s3_boto_client: boto3.client, moreapp_form: str) -> pd.DataFrame:
	"""Lê o CSV da silver, transforma e escreve Parquet na gold."""
	s3_bucket_silver = "dev-houer-us-east-1-silver-zone"
	print(f"\n--- Processando formulário: {moreapp_form} ---")
	s3_key_silver = find_latest_csv_for_form(s3_boto_client, s3_bucket_silver, moreapp_form)
	if not s3_key_silver:
		print(f"AVISO: Nenhum arquivo CSV encontrado para o formulário '{moreapp_form}'. Pulando.")
		return None
	try:
		csv_data = s3_phynfra_client.read(bucket=s3_bucket_silver, keyPrefix=s3_key_silver)
		if not csv_data:
			print("ALERTA: O arquivo CSV está vazio. Nenhum Parquet será gerado.")
			return None
	except Exception as e:
		print(f"ERRO ao baixar o CSV '{s3_key_silver}': {e}")
		return None
	print(f"Leitura do CSV '{s3_key_silver}' concluída com sucesso.")

	try:
		df = pd.read_csv(StringIO(csv_data), sep='|', engine='python', on_bad_lines='warn')
	except Exception as e:
		print(f"Falha CRÍTICA na leitura do CSV com o motor 'python'. Erro: {e}")
		return None

	print(f"Colunas encontradas para '{moreapp_form}': {df.columns.tolist()}")
	df.rename(columns={"mailStatuses_0_pdfFileId": "pdf_file_id"}, inplace=True)

	s3_bucket_gold = "dev-houer-us-east-1-gold-zone"

	s3_key_gold = f"{project}/moreapp/submissions/{moreapp_form}/{moreapp_form}.parquet"

	print(f"Tentando escrever Parquet em: s3://{s3_bucket_gold}/{s3_key_gold}")
	try:
		s3_phynfra_client.write(bucket=s3_bucket_gold, payload=df.to_parquet(index=False), keyPrefix=s3_key_gold)
		print("Escrita do Parquet na gold zone concluída com sucesso.")
	except Exception as e:
		print(f"ERRO ao escrever o Parquet na gold zone: {e}")
	return df


def generate_df_with_links(s3_boto_client: boto3.client, content: str, moreapp_form: str) -> pd.DataFrame:
	"""Gera um DataFrame com links para mídias."""
	s3_bucket_gold = "dev-houer-us-east-1-gold-zone"

	s3_key_gold = f"{project}/moreapp/submissions/{moreapp_form}/{moreapp_form}.parquet"

	try:
		obj = s3_boto_client.get_object(Bucket=s3_bucket_gold, Key=s3_key_gold)
		df = pd.read_parquet(BytesIO(obj['Body'].read()))
	except s3_boto_client.exceptions.NoSuchKey:
		return None
	except Exception as e:
		print(f"ERRO ao ler Parquet da Gold Zone para '{moreapp_form}': {e}")
		return None

	id_column_name = 'moreapp_submission_id' if 'moreapp_submission_id' in df.columns else df.columns[0]
	print(f"Usando a coluna '{id_column_name}' como ID para o formulário '{moreapp_form}'.")
	try:
		params = {}
		if content == "images":
			params = {"keywords": ["foto", "photo", "assinatura", "registrodaevidcia"], "id_col": "id_foto",
					  "val_col": "codigo_foto", "id_prefix": "gridfs://registrationFiles/", "is_melted": True}
		elif content == "videos":
			params = {"keywords": ["video"], "id_col": "id_video", "val_col": "codigo_video",
					  "id_prefix": "gridfs://registrationFiles/", "is_melted": True}
		elif content == "pdfs":
			params = {"keywords": ["pdf_file_id"], "id_col": "id_pdf", "val_col": "codigo_pdf", "id_prefix": None,
					  "is_melted": False}
		else:
			return None
		media_cols = [col for col in df.columns if any(kw in col.lower() for kw in params["keywords"])]
		if not media_cols: return None
		if params["is_melted"]:
			media_cols.append(id_column_name)
			df_media = pd.melt(df[media_cols], id_vars=[id_column_name], var_name="source_column",
							   value_name=params["val_col"])
		else:
			df_media = df[[id_column_name] + media_cols].copy()
			df_media.rename(columns={media_cols[0]: params["val_col"]}, inplace=True)
		df_media.dropna(subset=[params["val_col"]], inplace=True)
		if df_media.empty: return None
		if params["id_prefix"]:
			prefix = params["id_prefix"]
			df_media[params["id_col"]] = df_media[params["val_col"]].apply(
				lambda x: str(x).split(prefix)[1] if pd.notna(x) and prefix in str(x) else None)
		else:
			df_media[params["id_col"]] = df_media[params["val_col"]]
		df_media.dropna(subset=[params["id_col"]], inplace=True)
		if df_media.empty: return None
		files_in_s3 = scan_content_in_s3_bucket(s3_boto_client, content=content, moreapp_form=moreapp_form)
		if not files_in_s3: return None
		links = []
		for file_path in files_in_s3:
			file_id, _ = os.path.splitext(file_path)
			url_prefix = f"{project}/moreapp/{content}/{moreapp_form}/{file_path}"
			url = f"https://houer-vi-publico.s3.amazonaws.com/{url_prefix}"
			links.append({"file_id_from_s3": file_id, "url": url})
		if not links: return None
		df_links = pd.DataFrame(links)
		df_final = df_media.merge(df_links, left_on=params["id_col"], right_on='file_id_from_s3')
		df_final = df_final[[id_column_name, params["id_col"], "url"]]
		df_final.rename(
			columns={"url": "url_presigned", params["id_col"]: f"id_{content[:-1]}", id_column_name: "submission_id"},
			inplace=True)
		df_final["formulario_moreapp"] = moreapp_form
		return df_final
	except Exception as e:
		print(f"ERRO durante o processamento de '{content}' para o form '{moreapp_form}': {e}")
		return None


def main():
	"""Função principal de orquestração do ETL."""
	try:
		s3_phynfra_client = S3(region="us-east-1", accessKey=AWS_ACCESS_KEY, secretKey=AWS_SECRET_ACCESS_KEY)
		s3_boto_client = boto3.client('s3', region_name='us-east-1')
	except Exception as e:
		print(f"ERRO: Falha ao inicializar os clientes S3. Detalhes: {e}")
		return

	print("--- Iniciando Etapa 1: Conversão de CSV para Parquet ---")
	for form_name in moreapp_forms.keys():
		try:
			generate_final_df(s3_phynfra_client, s3_boto_client, moreapp_form=form_name)
		except Exception as e:
			print(f"Falha CRÍTICA ao processar form '{form_name}'. Error: {e}")
	print("--- Etapa 1 Concluída ---\n")

	print("--- Iniciando Etapa 2: Geração de Links de Mídia ---")
	for content_type in 1:
		print(f"\nProcessando tipo de conteúdo: '{content_type}'")
		list_of_link_dfs = []
		for form_name in moreapp_forms.keys():
			try:
				urls = generate_df_with_links(s3_boto_client, content=content_type, moreapp_form=form_name)
				if urls is not None and not urls.empty:
					list_of_link_dfs.append(urls)
			except Exception as e:
				print(f"ERRO ao gerar links para o formulário '{form_name}' (conteúdo: '{content_type}'): {e}")

		if list_of_link_dfs:
			final_urls_df = pd.concat(list_of_link_dfs, ignore_index=True)
			s3_bucket = "dev-houer-us-east-1-gold-zone"

			s3_id_key = f"{project}/moreapp/submissions/{content_type}/{content_type}.parquet"

			print(f"Escrevendo links consolidados de '{content_type}' em s3://{s3_bucket}/{s3_id_key}")
			s3_phynfra_client.write(bucket=s3_bucket, payload=final_urls_df.to_parquet(index=False),
									keyPrefix=s3_id_key)
		else:
			print(f"Nenhum link encontrado para o tipo de conteúdo: '{content_type}'")

	print("\nProcesso ETL finalizado.")


if __name__ == "__main__":
	main()
