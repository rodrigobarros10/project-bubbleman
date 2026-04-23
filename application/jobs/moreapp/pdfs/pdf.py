import boto3
import pandas as pd
import os
import requests
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURAÇÕES ---
SILVER_BUCKET = "dev-houer-us-east-1-silver-zone"
GOLD_BUCKET = "dev-houer-us-east-1-gold-zone"
PDF_DESTINATION_BUCKET = "houer-vi-publico"
AWS_REGION = "us-east-1"

BASE_PREFIXO_SILVER = "project-bubbleman/moreapp/submissions"
BASE_PREFIXO_GOLD = "project-bubbleman/moreapp/submissions/pdfs"

MOREAPP_CUSTOMER_ID = 163779
MOREAPP_CUSTOMER_ID = 163779
MAX_WORKERS_DOWNLOAD = 5  # Número de downloads simultâneos

# --- AUTENTICAÇÃO ---
MOREAPP_API_KEY = "kIQblHraCHvDC46fB2wJ8_XXWObF9D0dJW-dIU9aF2g="

try:
    # Inicializa cliente S3 Global com autenticação implícita (Ambiente/IAM)
    s3_client = boto3.client('s3', region_name=AWS_REGION)
except Exception as e:
    raise RuntimeError(f"Falha ao autenticar no AWS S3. Erro: {e}")

if not MOREAPP_API_KEY:
    raise ValueError("A variável MOREAPP_API_KEY está vazia.")


# --- FUNÇÕES AUXILIARES ---

def _gerar_s3_url(bucket: str, region: str, prefixo: str, nome_arquivo: str) -> str:
    if not nome_arquivo or not isinstance(nome_arquivo, str):
        return None
    return f"https://{bucket}.s3.{region}.amazonaws.com/{prefixo}{nome_arquivo}"


def identificar_coluna_id(df, nome_arquivo):
    candidatos = ['id', 'id_coleta', 'id_varricao', '_id']
    for col in candidatos:
        if col in df.columns:
            return col
    return None


def listar_pdfs_existentes_s3(bucket, prefixo):
    """Lista todos os PDFs que já existem no bucket de destino para evitar re-download."""
    existentes = set()
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix=prefixo)
        for page in pages:
            for obj in page.get('Contents', []):
                # Extrai apenas o ID do arquivo (nome sem extensão)
                nome_sem_ext = os.path.splitext(os.path.basename(obj['Key']))[0]
                existentes.add(nome_sem_ext)
    except Exception as e:
        print(f"  -> Erro ao verificar arquivos existentes no S3: {e}")
    return existentes


def worker_download_upload(pdf_id, prefixo_destino):
    """Função executada por thread individual para baixar e subir um único PDF."""
    if len(pdf_id) < 5: return False  # Ignora IDs quebrados

    url_download = f"https://api.moreapp.com/api/v1.0/customers/{MOREAPP_CUSTOMER_ID}/registrationFile/{pdf_id}/download"
    headers = {"X-Api-Key": MOREAPP_API_KEY}

    try:
        # Download da API
        resp = requests.get(url_download, headers=headers, timeout=60)
        if resp.status_code == 200:
            s3_key = f"{prefixo_destino}{pdf_id}.pdf"
            # Upload para o S3
            s3_client.put_object(
                Bucket=PDF_DESTINATION_BUCKET,
                Key=s3_key,
                Body=resp.content,
                ContentType='application/pdf'
            )
            return True
        else:
            print(f"    -> Falha API ({resp.status_code}) ID: {pdf_id}")
            return False
    except Exception as e:
        print(f"    -> Erro Exceção ID {pdf_id}: {e}")
        return False


# --- FASE 1: EXTRAÇÃO DE DADOS ---

def extrair_metadados_tabela(nome_tabela, prefixo_silver) -> pd.DataFrame:
    """Lê CSVs do S3 e monta o DataFrame de mapeamento (SEM BAIXAR PDFS)."""
    print(f"--- Processando metadados: '{nome_tabela}' ---")

    csv_files = []
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=SILVER_BUCKET, Prefix=prefixo_silver)
        csv_files = [obj['Key'] for page in pages for obj in page.get('Contents', []) if
                     obj['Key'].lower().endswith('.csv')]
    except Exception as e:
        print(f"  -> Erro ao listar S3: {e}")
        return None

    if not csv_files:
        return None

    lista_dfs = []

    for csv_key in csv_files:
        try:
            response = s3_client.get_object(Bucket=SILVER_BUCKET, Key=csv_key)
            content = response['Body'].read()

            # Tentativa de leitura (Pipe ou Vírgula)
            try:
                df = pd.read_csv(BytesIO(content), sep='|', dtype='object')
                if len(df.columns) <= 1:
                    df = pd.read_csv(BytesIO(content), sep=',', dtype='object')
            except:
                df = pd.read_csv(BytesIO(content), sep=',', dtype='object')

            col_id = identificar_coluna_id(df, csv_key)
            if not col_id: continue

            df_map = pd.DataFrame()

            # Lógica de extração do ID do PDF
            if nome_tabela == 'ndp':
                cols_pdf = [c for c in ['mailStatuses_0_pdfFileId', 'mailStatuses_1_pdfFileId'] if c in df.columns]
                if cols_pdf:
                    df_long = pd.melt(df, id_vars=[col_id], value_vars=cols_pdf, value_name='id_pdf')
                    df_map = df_long[[col_id, 'id_pdf']].dropna()
            else:
                if 'id_pdf' in df.columns:
                    df_map = df[[col_id, 'id_pdf']].dropna()
                elif 'mailStatuses_0_pdfFileId' in df.columns:
                    df_map = df[[col_id, 'mailStatuses_0_pdfFileId']].dropna()
                    df_map.columns = [col_id, 'id_pdf']

            if not df_map.empty:
                df_map = df_map.rename(columns={col_id: 'id_formulario'})
                lista_dfs.append(df_map)

        except Exception:
            continue

    if not lista_dfs:
        return None

    df_final = pd.concat(lista_dfs, ignore_index=True).drop_duplicates()
    df_final['nome_formulario'] = nome_tabela

    # Limpeza do ID do PDF (.0 no final)
    df_final['id_pdf'] = df_final['id_pdf'].astype(str).apply(lambda x: x[:-2] if x.endswith('.0') else x)

    # Gera a URL teórica (para salvar no parquet)
    prefixo_destino = f"project-starman/moreapp/pdfs/{nome_tabela}/"
    df_final['pdf_s3_url'] = df_final['id_pdf'].apply(
        lambda pid: _gerar_s3_url(PDF_DESTINATION_BUCKET, AWS_REGION, prefixo_destino, f"{pid}.pdf")
    )

    return df_final


# --- EXECUÇÃO PRINCIPAL ---

if __name__ == "__main__":
    tabelas = ["irsp", "irsv", "irsf", "irss", "ilum", "ilup", "amb", "irsrsd"]
    dfs_para_consolidar = []

    print("\n=== PASSO 1: LEITURA E CONSOLIDAÇÃO DE DADOS ===")

    for tbl in tabelas:
        prefixo = f"{BASE_PREFIXO_SILVER}/{tbl}/"
        df_tbl = extrair_metadados_tabela(tbl, prefixo)
        if df_tbl is not None:
            dfs_para_consolidar.append(df_tbl)

    if not dfs_para_consolidar:
        print("Nenhum dado encontrado. Encerrando.")
        exit()

    # Consolidar tudo
    df_gold = pd.concat(dfs_para_consolidar, ignore_index=True)
    df_gold.drop_duplicates(subset=['id_formulario', 'id_pdf'], inplace=True)

    print(f"\n=== PASSO 2: SALVANDO PARQUET ({len(df_gold)} registros) ===")
    gold_path = f"s3://{GOLD_BUCKET}/{BASE_PREFIXO_GOLD}/pdfs.parquet"

    try:
        df_gold.to_parquet(
            gold_path,
            index=False,
            engine='pyarrow'
        )
        print(f"-> SUCESSO: Parquet salvo e seguro em {gold_path}")
    except Exception as e:
        print(f"-> ERRO CRÍTICO AO SALVAR PARQUET: {e}")
        print("-> Salvando backup local...")
        df_gold.to_parquet("backup_emergencia_pdfs.parquet", index=False)

    print("\n=== PASSO 3: SINCRONIZAÇÃO DE ARQUIVOS (DOWNLOAD/UPLOAD) ===")

    # Agrupa por tabela para gerenciar prefixos corretamente
    grupos = df_gold.groupby('nome_formulario')

    total_sucessos = 0
    total_erros = 0

    for nome_tabela, grupo in grupos:
        prefixo_destino_pdf = f"project-starman/moreapp/pdfs/{nome_tabela}/"
        print(f"\nVerificando tabela: {nome_tabela}")

        # 1. Verifica o que já existe no S3
        ids_existentes = listar_pdfs_existentes_s3(PDF_DESTINATION_BUCKET, prefixo_destino_pdf)

        # 2. Filtra o que precisa baixar
        todos_ids = set(grupo['id_pdf'].unique())
        ids_para_baixar = list(todos_ids - ids_existentes)

        if not ids_para_baixar:
            print("  -> Todos os PDFs já estão sincronizados.")
            continue

        print(f"  -> Iniciando download de {len(ids_para_baixar)} arquivos em paralelo...")

        # 3. Execução em Paralelo
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_DOWNLOAD) as executor:
            # Submete tarefas
            futures = {
                executor.submit(worker_download_upload, pdf_id, prefixo_destino_pdf): pdf_id
                for pdf_id in ids_para_baixar
            }

            # Processa conforme terminam
            for future in as_completed(futures):
                if future.result():
                    total_sucessos += 1
                else:
                    total_erros += 1

    print(f"\n=== PROCESSO FINALIZADO ===")
    print(f"Total Novos Baixados: {total_sucessos}")
    print(f"Total Falhas: {total_erros}")