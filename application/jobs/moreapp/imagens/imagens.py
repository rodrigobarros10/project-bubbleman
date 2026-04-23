import boto3
import pandas as pd
import os
import requests
import re
import concurrent.futures
from io import BytesIO
from urllib.parse import urlparse
from botocore.exceptions import ClientError

# --- CONFIGURAÇÕES ---
SILVER_BUCKET = "dev-houer-us-east-1-silver-zone"
GOLD_BUCKET = "dev-houer-us-east-1-gold-zone"
PUBLIC_BUCKET = "houer-vi-publico"
AWS_REGION = "us-east-1"

BASE_PREFIXO_SILVER = "project-bubbleman/moreapp/submissions"
BASE_PREFIXO_GOLD_IMAGENS = "project-bubbleman/moreapp/submissions/imagens"
BASE_PREFIXO_GOLD_VIDEOS = "project-bubbleman/moreapp/submissions/videos"
BASE_PREFIXO_IMAGENS_DESTINO = "project-bubbleman/moreapp/imagens/"

MOREAPP_CUSTOMER_ID = 163779
MAX_WORKERS = 20  # Número de downloads/uploads simultâneos

# --- AUTENTICAÇÃO ---
MOREAPP_API_KEY = "kIQblHraCHvDC46fB2wJ8_XXWObF9D0dJW-dIU9aF2g=" 

try:
    # Cliente S3 (Boto3 clients são thread-safe)
    # Autenticação implícita via ambiente/IAM Role
    s3_client = boto3.client('s3', region_name=AWS_REGION)
except Exception as e:
    raise RuntimeError(f"Falha ao autenticar no AWS S3. Erro: {e}")

if not MOREAPP_API_KEY:
    raise ValueError("A variável MOREAPP_API_KEY está vazia.")

# Sessão Global para Requests (Reuso de conexão TCP)
session = requests.Session()
session.headers.update({"X-Api-Key": MOREAPP_API_KEY})


# Regex compilados globalmente
REGEX_FOTO = re.compile(r'foto_(\d+)_url|foto_url')
REGEX_VIDEO = re.compile(r'video_(\d+)_url|video_url')
REGEX_GRIDFS = re.compile(r'registrationFiles/([a-zA-Z0-9-]+)')


def _extrair_id_da_url(url: str) -> str:
	if not isinstance(url, str) or not url.strip():
		return None
	try:
		match = REGEX_GRIDFS.search(url)
		if match:
			return match.group(1)
		return os.path.splitext(os.path.basename(urlparse(url).path))[0]
	except Exception:
		return None


def _gerar_s3_url(bucket: str, region: str, prefixo: str, nome_arquivo: str) -> str:
	if pd.isna(nome_arquivo) or not nome_arquivo:
		return None
	return f"https://{bucket}.s3.{region}.amazonaws.com/{prefixo}{nome_arquivo}"


def _determinar_url_download(row):
	"""Função auxiliar para aplicar no DataFrame e determinar URL de download."""
	url_original = row['url_original']
	file_id = row['file_id']

	if isinstance(url_original, str) and 'gridfs://' in url_original:
		return f"https://api.moreapp.com/api/v1.0/customers/{MOREAPP_CUSTOMER_ID}/registrationFile/{file_id}/download"
	elif isinstance(url_original, str) and url_original.startswith('http'):
		return url_original
	return None


def transferir_arquivo(item):
	"""
	Função executada em paralelo para baixar e subir o arquivo.
	"""
	url_download = item['url']
	nome_arquivo = item['nome_arquivo']
	prefixo_destino = BASE_PREFIXO_IMAGENS_DESTINO
	bucket_destino = PUBLIC_BUCKET

	try:
		# Download (stream)
		with session.get(url_download, stream=True, timeout=30) as r:
			r.raise_for_status()

			# Upload direto (stream) sem salvar em disco
			# Determina content type
			ext = nome_arquivo.lower().split('.')[-1]
			content_type = 'image/jpeg' if ext in ['jpg',
												   'jpeg'] else 'video/mp4' if ext == 'mp4' else 'application/octet-stream'

			s3_key = f"{prefixo_destino}{nome_arquivo}"
			s3_client.upload_fileobj(
				r.raw,
				bucket_destino,
				s3_key,
				ExtraArgs={'ContentType': content_type}
			)
		return True
	except Exception as e:
		print(f"    [ERRO] Falha em {nome_arquivo}: {e}")
		return False


def extrair_dados_formulario(silver_bucket: str, silver_prefixo_tabela: str):
	nome_formulario = silver_prefixo_tabela.strip('/').split('/')[-1]
	print(f"--- Processando Tabela: '{nome_formulario}' ---")

	dfs_fotos = []
	dfs_videos = []

	try:
		# Listagem eficiente de objetos
		paginator = s3_client.get_paginator('list_objects_v2')
		pages = paginator.paginate(Bucket=silver_bucket, Prefix=silver_prefixo_tabela)

		csv_keys = []
		for page in pages:
			if 'Contents' in page:
				csv_keys.extend([obj['Key'] for obj in page['Contents'] if obj['Key'].lower().endswith('.csv')])

		if not csv_keys:
			return None, None

		# Processar cada CSV
		for csv_key in csv_keys:
			response = s3_client.get_object(Bucket=silver_bucket, Key=csv_key)
			df = pd.read_csv(BytesIO(response['Body'].read()), sep='|')

			# Identificar ID
			id_col = next((col for col in ['id', 'id_coleta', 'id_varricao', 'id_formulario'] if col in df.columns),
						  df.columns[0])

			# --- PROCESSAMENTO FOTOS (Vetorizado) ---
			cols_foto = [c for c in df.columns if REGEX_FOTO.search(c)]
			for col in cols_foto:
				match = re.search(r'foto_(\d+)_url', col)
				num_foto = int(match.group(1)) if match else 1

				# Filtra apenas linhas válidas
				df_temp = df.loc[df[col].notna(), [id_col, col]].copy()
				if df_temp.empty: continue

				df_temp.rename(columns={id_col: 'id_formulario', col: 'url_original'}, inplace=True)
				df_temp['campo_descricao_foto'] = col
				df_temp['numero_foto'] = num_foto
				df_temp['descricao_foto'] = pd.NA

				# Extração vetorizada de ID
				df_temp['id_foto_moreapp'] = df_temp['url_original'].apply(_extrair_id_da_url)
				df_temp.dropna(subset=['id_foto_moreapp'], inplace=True)

				# Prepara colunas para lógica de download
				df_temp['file_id'] = df_temp['id_foto_moreapp']  # Alias para função auxiliar
				df_temp['url_download'] = df_temp.apply(_determinar_url_download, axis=1)
				df_temp['nome_arquivo_destino'] = df_temp['id_foto_moreapp'] + ".jpg"

				# URL final pública
				df_temp['url_bucket_publico'] = df_temp['nome_arquivo_destino'].apply(
					lambda x: _gerar_s3_url(PUBLIC_BUCKET, AWS_REGION, BASE_PREFIXO_IMAGENS_DESTINO, x)
				)

				dfs_fotos.append(df_temp)

			# --- PROCESSAMENTO VIDEOS (Vetorizado) ---
			cols_video = [c for c in df.columns if
						  REGEX_VIDEO.search(c) or ('video' in c.lower() and 'url' in c.lower())]
			for col in cols_video:
				match = re.search(r'video_(\d+)_url', col)
				num_video = int(match.group(1)) if match else 1

				df_temp = df.loc[df[col].notna(), [id_col, col]].copy()
				if df_temp.empty: continue

				df_temp.rename(columns={id_col: 'id_formulario', col: 'url_original'}, inplace=True)
				df_temp['campo_descricao_video'] = col
				df_temp['numero_video'] = num_video
				df_temp['descricao_video'] = pd.NA

				df_temp['id_video_moreapp'] = df_temp['url_original'].apply(_extrair_id_da_url)
				df_temp.dropna(subset=['id_video_moreapp'], inplace=True)

				df_temp['file_id'] = df_temp['id_video_moreapp']
				df_temp['url_download'] = df_temp.apply(_determinar_url_download, axis=1)
				df_temp['nome_arquivo_destino'] = df_temp['id_video_moreapp'] + ".mp4"

				df_temp['url_bucket_publico'] = df_temp['nome_arquivo_destino'].apply(
					lambda x: _gerar_s3_url(PUBLIC_BUCKET, AWS_REGION, BASE_PREFIXO_IMAGENS_DESTINO, x)
				)

				dfs_videos.append(df_temp)

	except Exception as e:
		print(f"  [ERRO] Processando bucket {silver_bucket}: {e}")
		return None, None

	# Consolidação final por formulário
	df_final_fotos = pd.concat(dfs_fotos, ignore_index=True) if dfs_fotos else None
	if df_final_fotos is not None: df_final_fotos['nome_formulario'] = nome_formulario

	df_final_videos = pd.concat(dfs_videos, ignore_index=True) if dfs_videos else None
	if df_final_videos is not None: df_final_videos['nome_formulario'] = nome_formulario

	return df_final_fotos, df_final_videos


def salvar_e_sincronizar(df_total, bucket_gold, prefixo_gold, parquet_name, colunas_finais, id_col, drop_cols, tipo):
	if df_total is None or df_total.empty:
		print(f"\n--- Nenhum dado de {tipo} para processar. ---")
		return

	print(f"\n--- Iniciando Persistência e Sincronização: {tipo} ---")

	# 1. Limpeza e Salvamento Parquet
	df_total.dropna(subset=[id_col], inplace=True)
	cols_existentes_drop = [c for c in drop_cols if c in df_total.columns]
	df_total.drop_duplicates(subset=cols_existentes_drop, inplace=True)

	cols_validas = [c for c in colunas_finais if c in df_total.columns]
	df_save = df_total[cols_validas]

	path_gold = f"s3://{bucket_gold}/{prefixo_gold}/{parquet_name}"
	print(f"  -> Salvando Parquet: {path_gold}")
	try:
		df_save.to_parquet(path_gold, index=False)
	except Exception as e:
		print(f"  [ERRO] Ao salvar Parquet: {e}")

	# 2. Preparação para Sincronização
	# Filtra apenas o que tem URL de download válida
	df_sync = df_total.dropna(subset=['url_download']).drop_duplicates(subset=['nome_arquivo_destino'])

	arquivos_para_processar = []

	# 3. Verifica arquivos já existentes no destino (Otimização: Listar apenas uma vez)
	print("  -> Verificando arquivos existentes no S3 Público...")
	midias_existentes = set()
	try:
		paginator = s3_client.get_paginator('list_objects_v2')
		for page in paginator.paginate(Bucket=PUBLIC_BUCKET, Prefix=BASE_PREFIXO_IMAGENS_DESTINO):
			if 'Contents' in page:
				midias_existentes.update(os.path.basename(obj['Key']) for obj in page['Contents'])
	except Exception as e:
		print(f"  [AVISO] Não foi possível listar destino ({e}).")

	# Monta lista de tarefas
	for _, row in df_sync.iterrows():
		if row['nome_arquivo_destino'] not in midias_existentes:
			arquivos_para_processar.append({
				'url': row['url_download'],
				'nome_arquivo': row['nome_arquivo_destino']
			})

	total_arquivos = len(arquivos_para_processar)
	if total_arquivos == 0:
		print("  -> Todos os arquivos já estão sincronizados.")
		return

	print(f"  -> Iniciando download/upload de {total_arquivos} arquivos usando {MAX_WORKERS} threads...")

	# 4. Execução Paralela
	sucesso_count = 0
	with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
		# Submit tasks
		futures = {executor.submit(transferir_arquivo, item): item for item in arquivos_para_processar}

		for i, future in enumerate(concurrent.futures.as_completed(futures)):
			if future.result():
				sucesso_count += 1

			# Feedback visual de progresso simples
			if (i + 1) % 10 == 0:
				print(f"    Progresso: {i + 1}/{total_arquivos} concluídos.", end='\r')

	print(f"\n  -> Sincronização finalizada. Sucesso: {sucesso_count}/{total_arquivos}")


if __name__ == "__main__":
	FORMULARIOS = ["irsp", "irsv", "irsf", "irss", "ilum", "ilup", "amb", "irsrsd"]

	COLS_FIM_IMG = ['id_formulario', 'nome_formulario', 'campo_descricao_foto', 'numero_foto', 'descricao_foto',
					'id_foto_moreapp', 'url_bucket_publico']
	COLS_FIM_VID = ['id_formulario', 'nome_formulario', 'campo_descricao_video', 'numero_video', 'descricao_video',
					'id_video_moreapp', 'url_bucket_publico']

	all_fotos = []
	all_videos = []

	# Extração dos dados
	for form in FORMULARIOS:
		df_f, df_v = extrair_dados_formulario(SILVER_BUCKET, f"{BASE_PREFIXO_SILVER}/{form}/")
		if df_f is not None: all_fotos.append(df_f)
		if df_v is not None: all_videos.append(df_v)

	# Processamento Final Imagens
	df_concat_fotos = pd.concat(all_fotos, ignore_index=True) if all_fotos else None
	salvar_e_sincronizar(
		df_concat_fotos, GOLD_BUCKET, BASE_PREFIXO_GOLD_IMAGENS, "imagens.parquet",
		COLS_FIM_IMG, 'id_foto_moreapp', ['id_formulario', 'campo_descricao_foto', 'id_foto_moreapp'], "IMAGENS"
	)

	# Processamento Final Vídeos
	df_concat_videos = pd.concat(all_videos, ignore_index=True) if all_videos else None
	salvar_e_sincronizar(
		df_concat_videos, GOLD_BUCKET, BASE_PREFIXO_GOLD_VIDEOS, "videos.parquet",
		COLS_FIM_VID, 'id_video_moreapp', ['id_formulario', 'campo_descricao_video', 'id_video_moreapp'], "VIDEOS"
	)