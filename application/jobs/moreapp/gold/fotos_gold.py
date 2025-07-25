import boto3
import json
import os
import requests
import time
import unicodedata
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional, Generator
from botocore.exceptions import ClientError
import logging
from urllib.parse import urlparse

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('moreapp_photos_processor.log')
    ]
)
logger = logging.getLogger(__name__)

class MoreAppAPIClient:
    """Cliente para interação com a API do MoreApp"""
    
    BASE_URL = "https://api.moreapp.com"
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    
    def __init__(self, api_key: str, customer_id: str = "163779"):
        self.api_key = api_key
        self.customer_id = customer_id
        self.session = requests.Session()
        self._configure_session()
    
    def _configure_session(self):
        """Configura a sessão HTTP com headers padrão"""
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Api-Key": self.api_key,
            "User-Agent": "MoreAppPhotoProcessor/1.0"
        })
    
    def download_file(self, file_id: str) -> Optional[BytesIO]:
        """Baixa um arquivo da API do MoreApp com tratamento de erros"""
        url = f"{self.BASE_URL}/api/v1/files/{file_id}/download"
        return self._download_with_retry(url, file_id)
    
    def download_registration_file(self, file_id: str) -> Optional[BytesIO]:
        """Baixa um arquivo de registro da API do MoreApp"""
        url = f"{self.BASE_URL}/api/v1.0/customers/{self.customer_id}/registrationFile/{file_id}/download"
        return self._download_with_retry(url, file_id)
    
    def _download_with_retry(self, url: str, file_id: str) -> Optional[BytesIO]:
        """Lógica comum de download com tratamento de retry"""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.get(
                    url,
                    headers={'Accept': '*/*'},
                    stream=True,
                    timeout=30
                )
                
                if response.status_code == 403:
                    error_detail = response.json().get('message', 'Sem mensagem de erro')
                    raise PermissionError(f"Acesso negado (403): {error_detail}")
                elif response.status_code == 404:
                    logger.warning(f"Arquivo não encontrado (404): {file_id}")
                    return None
                
                response.raise_for_status()
                
                content_type = response.headers.get('content-type', '')
                if 'image' not in content_type:
                    logger.warning(f"Content-Type não é imagem: {content_type}")
                    return None
                
                return BytesIO(response.content)
                
            except PermissionError as e:
                logger.error(f"Erro de permissão: {str(e)}")
                break
            except requests.exceptions.RequestException as e:
                logger.warning(f"Tentativa {attempt + 1} falhou para {file_id}: {str(e)}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY * (attempt + 1))
                continue
            except Exception as e:
                logger.error(f"Erro inesperado ao baixar {file_id}: {str(e)}")
                break
        
        return None

class S3Manager:
    """Gerenciador de operações com Amazon S3"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.client = boto3.client('s3', region_name=region)
    
    def list_objects(self, bucket: str, prefix: str) -> Generator[Dict, None, None]:
        """Lista objetos em um bucket S3 com paginação"""
        paginator = self.client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
        
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    yield obj
    
    def get_json_file(self, bucket: str, key: str) -> Optional[Dict]:
        """Baixa e parseia um arquivo JSON do S3"""
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('windows-1252')
            return json.loads(content)
        except (ClientError, json.JSONDecodeError) as e:
            logger.error(f"Erro ao ler JSON {bucket}/{key}: {str(e)}")
            return None
    
    def upload_image(self, image_data: BytesIO, bucket: str, key: str, metadata: Dict) -> bool:
        """Faz upload de uma imagem para o S3"""
        try:
            image_data.seek(0)
            self.client.upload_fileobj(
                image_data,
                bucket,
                key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    'Metadata': metadata
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Erro ao fazer upload para {bucket}/{key}: {str(e)}")
            return False
    
    def check_file_exists(self, bucket: str, key: str) -> bool:
        """Verifica se um arquivo existe no S3"""
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

class MoreAppPhotoProcessor:
    """Processa fotos dos formulários do MoreApp e salva no S3 Gold"""
    
    def __init__(self, api_key: str, customer_id: str = "163779"):
        self.api_client = MoreAppAPIClient(api_key, customer_id)
        self.s3_manager = S3Manager()
        
        # Configurações dos buckets
        self.landing_bucket = "dev-houer-us-east-1-landing-zone"
        self.gold_bucket = "dev-houer-us-east-1-gold-zone"
        self.landing_prefix = "project-bubbleman/moreapp/submissions/"
        self.gold_prefix = "project-bubbleman/moreapp/submissions/fotos/"
    
    def _sanitize_metadata(self, metadata: Dict[str, str]) -> Dict[str, str]:
        """
        Remove caracteres não-ASCII dos metadados para compatibilidade com S3
        
        Args:
            metadata: Dicionário com metadados originais
            
        Returns:
            Dicionário com metadados sanitizados (apenas ASCII)
        """
        sanitized = {}
        for key, value in metadata.items():
            # Remove acentos e caracteres especiais
            normalized = unicodedata.normalize('NFKD', str(value))
            ascii_value = normalized.encode('ascii', 'ignore').decode('ascii')
            sanitized[key] = ascii_value
        return sanitized
    
    def extract_photo_urls(self, form_data: Dict) -> Generator[str, None, None]:
        """Extrai URLs de fotos de um formulário"""
        if not isinstance(form_data, dict):
            return
            
        def _find_urls(data: Any):
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str) and value.startswith('gridfs://'):
                        yield value
                    else:
                        yield from _find_urls(value)
            elif isinstance(data, list):
                for item in data:
                    yield from _find_urls(item)
        
        yield from _find_urls(form_data)
    
    def process_form_photos(self, form_name: str, form_data: List[Dict]):
        """Processa fotos de um único formulário"""
        logger.info(f"Processando fotos do formulário: {form_name}")
        
        photo_count = 0
        skipped_count = 0
        error_count = 0
        
        for record in form_data:
            for gridfs_url in self.extract_photo_urls(record):
                try:
                    file_id = gridfs_url.split('/')[-1].replace('\\', '')
                    
                    date_str = datetime.now().strftime('%Y/%m/%d')
                    filename = f"{file_id}.jpg"
                    s3_key = f"{self.gold_prefix}{form_name}/{filename}"
                    
                    if self.s3_manager.check_file_exists(self.gold_bucket, s3_key):
                        logger.debug(f"Foto {file_id} já existe, pulando")
                        skipped_count += 1
                        continue
                    
                    logger.debug(f"Baixando foto: {file_id}")
                    image_data = self.api_client.download_registration_file(file_id)
                    
                    if not image_data:
                        logger.debug(f"Tentando método alternativo para {file_id}")
                        image_data = self.api_client.download_file(file_id)
                    
                    if not image_data:
                        error_count += 1
                        continue
                    
                    metadata = {
                        'source': 'moreapp-api',
                        'form_name': form_name,
                        'original_gridfs_url': gridfs_url,
                        'file_id': file_id,
                        'processing_date': datetime.now().isoformat()
                    }
                    sanitized_metadata = self._sanitize_metadata(metadata)
                    
                    if self.s3_manager.upload_image(image_data, self.gold_bucket, s3_key, sanitized_metadata):
                        photo_count += 1
                        logger.info(f"Foto {file_id} salva em s3://{self.gold_bucket}/{s3_key}")
                    else:
                        error_count += 1
                
                except Exception as e:
                    error_count += 1
                    logger.error(f"Erro ao processar foto {gridfs_url}: {str(e)}")
        
        logger.info(f"Resumo para {form_name}:")
        logger.info(f"- Fotos processadas: {photo_count}")
        logger.info(f"- Fotos puladas (já existiam): {skipped_count}")
        logger.info(f"- Erros encontrados: {error_count}")
    
    def process_all_forms(self):
        """Processa fotos de todos os formulários na landing zone"""
        logger.info("Iniciando processamento de todas as fotos")
        
        total_photos = 0
        
        for obj in self.s3_manager.list_objects(self.landing_bucket, self.landing_prefix):
            if not obj['Key'].endswith('.json'):
                continue
                
            try:
                form_name = obj['Key'].split('/')[-2]
                form_data = self.s3_manager.get_json_file(self.landing_bucket, obj['Key'])
                if not form_data:
                    continue
                
                self.process_form_photos(form_name, form_data)
                
            except Exception as e:
                logger.error(f"Erro ao processar arquivo {obj['Key']}: {str(e)}")
        
        logger.info(f"Processamento completo. Total de fotos processadas: {total_photos}")

if __name__ == "__main__":
    try:
        API_KEY = os.getenv('MOREAPP_API_KEY', "kIQblHraCHvDC46fB2wJ8_XXWObF9D0dJW-dIU9aF2g=")
        CUSTOMER_ID = os.getenv('MOREAPP_CUSTOMER_ID', "163779")
        
        processor = MoreAppPhotoProcessor(API_KEY, CUSTOMER_ID)
        processor.process_all_forms()
    except PermissionError as e:
        logger.error(f"ERRO CRÍTICO: {str(e)}")
        logger.error("Verifique se a API Key está correta e tem permissões adequadas")
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
