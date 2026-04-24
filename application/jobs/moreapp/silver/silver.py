import boto3
import pandas as pd
import os
from io import StringIO
import tempfile
import ftfy



def corrigir_caracteres_definitiva(texto: str) -> str:
    """
    Função de diagnóstico e correção agressiva para problemas de encoding.
    """
    if pd.isna(texto) or not isinstance(texto, str):
        return texto

    try:
        texto_corrigido = texto.encode('latin-1').decode('utf-8')

        if "Ã" not in texto_corrigido:
            texto = texto_corrigido
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    texto = ftfy.fix_text(texto)

    return texto


def ler_csv_da_bronze(caminho_local: str) -> pd.DataFrame:
    """
    Lê um CSV da camada bronze, testando diferentes encodings para evitar erros.
    """
    encodings_para_tentar = ['windows-1252', 'latin-1', 'iso-8859-1']

    for encoding in encodings_para_tentar:
        try:
            df = pd.read_csv(
                caminho_local,
                delimiter='|',
                dtype=str,
                low_memory=False,
                encoding=encoding
            )
            print(f"  -> Arquivo lido com sucesso usando encoding: '{encoding}'.")

            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].apply(corrigir_caracteres_definitiva)

            print(f"  -> Caracteres corrigidos.")
            return df

        except UnicodeDecodeError:
            print(f"  -> Falha ao ler com '{encoding}'. Tentando próximo...")
            continue
        except Exception as e:
            print(f"  -> Erro inesperado ao ler o arquivo CSV {caminho_local} com encoding '{encoding}': {e}")
            raise

    raise ValueError(
        f"Não foi possível ler o arquivo '{os.path.basename(caminho_local)}' com nenhum dos encodings testados.")



def _transform_ilu_produtividade(df: pd.DataFrame) -> dict:
    """Transforma dados do formulário ILU - Produtividade."""
    print("  -> Aplicando transformação de 'ILU - Produtividade'.")

    colunas_relevantes = {
        'id': 'id_coleta', 'meta_serialNumber': 'SN', 'data_buscar_id': 'id_buscar',
        'info_date': 'data_registro', 'data_regiao': 'codigo_regiao',
        'data_buscar_REGIAO': 'nome_regiao', 'data_buscar_SETOR': 'setor',
        'data_buscar_LOGRADOURO': 'logradouro', 'data_buscar_FREQUENCIA': 'frequencia_varricao',
        'data_buscar_EXTENSAOKM': 'extensao_km', 'data_responsavel_setor': 'responsavel_setor',
        'data_varredor': 'varredor', 'data_servico_executado': 'equipado_epi',
        'data_observacao': 'observacao', 'info_userId': 'operador_id',
        'meta_location_latitude': 'latitude', 'meta_location_longitude': 'longitude',
        'meta_registrationDate': 'data_registro_dispositivo',
        '_processing_timestamp': 'data_processamento', 'data_foto': 'foto_1_url',
        'data_foto2': 'foto_2_url', 'data_foto3': 'foto_3_url','mailStatuses_0_pdfFileId':'id_pdf'
    }

    colunas_existentes = {k: v for k, v in colunas_relevantes.items() if k in df.columns}
    df_silver = df[list(colunas_existentes.keys())].rename(columns=colunas_existentes)

    if 'data_registro' in df_silver.columns:
        df_silver['data_registro'] = pd.to_datetime(pd.to_numeric(df_silver['data_registro'], errors='coerce'), unit='ms', errors='coerce')
    if 'data_registro_dispositivo' in df_silver.columns:
        df_silver['data_registro_dispositivo'] = pd.to_datetime(pd.to_numeric(df_silver['data_registro_dispositivo'], errors='coerce'), unit='ms', errors='coerce')
    if 'data_processamento' in df_silver.columns:
        df_silver['data_processamento'] = pd.to_datetime(df_silver['data_processamento'], errors='coerce')

    colunas_numericas = ['extensao_km', 'latitude', 'longitude']
    for col in colunas_numericas:
        if col in df_silver.columns:
            df_silver[col] = pd.to_numeric(df_silver[col], errors='coerce')

    if 'servico_executado' in df_silver.columns:
        df_silver['servico_executado'] = df_silver['servico_executado'].apply(
            lambda x: True if str(x).lower() in ['sim', 'true', '1'] else False
        )


    metadados = {
        'quantidade_registros': len(df_silver),
        'periodo_inicio': df_silver['data_registro'].min() if 'data_registro' in df_silver.columns else None,
        'periodo_fim': df_silver['data_registro'].max() if 'data_registro' in df_silver.columns else None,
        'colunas_disponiveis': list(df_silver.columns)
    }

    return {
        "ilup": df_silver,
        # "Metadados_Produtividade": metadados
    }


def _transform_irs_coleta_rsd_frota(df: pd.DataFrame) -> dict:
    """Transforma dados do formulário 'IRS - Coleta RSD - Frota'."""

    print("  -> Aplicando transformação de 'IRS - Coleta RSD - Frota'.")

    colunas_relevantes = {
        'id': 'id_coleta',
        'meta_serialNumber': 'SN',
        'data_buscar_veiculo_id': 'id_veiculo',
        'info_date': 'data_coleta',
        'data_buscar_veiculo_PLACA': 'placa_veiculo',
        'data_buscar_veiculo_TIPODEVEICULO': 'tipo_veiculo',
        'data_buscar_veiculo_MODELO': 'modelo_veiculo',
        'data_buscar_veiculo_MARCA': 'marca_veiculo',
        'data_buscar_veiculo_ANODOMODELO': 'ano_modelo',
        'data_buscar_veiculo_lIMITEDACARGAPBTT': 'limite_carga_pbt',
        'data_buscar_veiculo_lIMITEDACARGAPBTCOMTOLERANCIAT': 'limite_carga_pbt_tolerancia',
        'data_nome_motorista': 'motorista',
        'data_coletor': 'coletor',
        'data_observacao': 'observacao',
        'data_foto': 'foto_1_url',
        'data_foto2': 'foto_2_url',
        'data_foto3': 'foto_3_url',
        'info_userId': 'operador_id',
        'meta_location_latitude': 'latitude',
        'meta_location_longitude': 'longitude',
        'meta_device_name': 'dispositivo',
        'meta_registrationDate': 'data_registro',
        'data_modelo_caminhao': 'modelo_caminhao',
        'mailStatuses_0_pdfFileId':'id_pdf'
    }

    colunas_existentes = {k: v for k, v in colunas_relevantes.items() if k in df.columns}
    df_silver = df[list(colunas_existentes.keys())].rename(columns=colunas_existentes)

  

    colunas_numericas = ['latitude', 'longitude', 'limite_carga_pbt', 'limite_carga_pbt_tolerancia']
    for col in colunas_numericas:
        if col in df_silver.columns:
            df_silver[col] = pd.to_numeric(df_silver[col], errors='coerce')

    if 'placa_veiculo' in df_silver.columns:
        df_silver['placa_veiculo'] = df_silver['placa_veiculo'].str.upper().str.strip()

    if 'motorista' in df_silver.columns:
        df_silver['motorista'] = df_silver['motorista'].str.title().str.strip()

    if 'data_coleta' in df_silver.columns:
        df_silver['data_coleta'] = pd.to_datetime(
            pd.to_numeric(df_silver['data_coleta'], errors='coerce'), 
            unit='ms', 
            errors='coerce'
        ).dt.strftime('%Y-%m-%d %H:%M:%S')
        
    if 'data_registro' in df_silver.columns:
        df_silver['data_registro'] = pd.to_datetime(
            pd.to_numeric(df_silver['data_registro'], errors='coerce'),
            unit='ms', 
            errors='coerce'
        ).dt.strftime('%Y-%m-%d %H:%M:%S')

    return {"irsf": df_silver}

def transform_irsrsd_coleta(df: pd.DataFrame) -> dict:
    """Transforma dados do formulário 'IRS - Coleta RSD - Frota'."""

    print("  -> Aplicando transformação de 'IRS/RSD - Coleta'.")

    colunas_relevantes = {
        'id': 'id_coleta',
        'data_dataEHoraDaVistoria': 'data_hora',
        'data_location_location_road': 'logradouro',
		'data_location_location_houseNumber': 'numero',
		'data_location_location_city':'municipio',
		'data_location_location_postcode':'cep',
		'data_location_location_country':'pais',
		'data_rota_SETOR':'setor_rota',
		'data_rota_LOCAL':'local_setor',
		'data_rota_DIA':'dia_rota',
		'data_rota_id':'id_rota',
		'data_logradouros_setor':'logradouro_setor',
		'data_logradouros_local':'logradouro_local',
		'data_logradouros_itinerario':'itinerario_logradouros',
		'data_logradouros_rua':'rua_logradouro',
		'data_logradouros_rota':'rota_logradouro',
		'data_logradouros_id':'id_logradouro',
		'data_servioExecutadoConformePlanejado':'executado_planejado',
		'data_observao':'observacao',
        'data_foto': 'foto_url',
		'data_foto1': 'foto_1_url',
        'data_foto2': 'foto_2_url',
        'data_foto3': 'foto_3_url',
		'data_foto4': 'foto_4_url',
		'data_foto5': 'foto_5_url',
        'info_customerId': 'id_inspetor',
        'info_userId':'email_inspetor'
    }

    colunas_existentes = {k: v for k, v in colunas_relevantes.items() if k in df.columns}
    df_silver = df[list(colunas_existentes.keys())].rename(columns=colunas_existentes)

    df_silver['data_hora'] = pd.to_datetime(df_silver['data_hora'], unit='ms', errors='coerce')

    colunas_numericas = ['latitude', 'longitude', 'id_inspetor', 'numero','id_rota','id_logradouro',]
    for col in colunas_numericas:
        if col in df_silver.columns:
            df_silver[col] = pd.to_numeric(df_silver[col], errors='coerce')

    if 'placa_veiculo' in df_silver.columns:
        df_silver['placa_veiculo'] = df_silver['placa_veiculo'].str.upper().str.strip()

    if 'motorista' in df_silver.columns:
        df_silver['motorista'] = df_silver['motorista'].str.title().str.strip()

    if 'data_hora' in df_silver.columns:
        df_silver['data_hora'] = pd.to_datetime(pd.to_numeric(df_silver['data_hora'], errors='coerce'), unit='ms',
                                                  errors='coerce')
    return {"irsrsd": df_silver}


def _transform_ambiental_irs_coleta_seletiva(df: pd.DataFrame) -> dict:
    """Transforma dados do formulário 'Ambiental - IRS - Coleta Seletiva'."""
    print("  -> Aplicando transformação de 'Ambiental - IRS - Coleta Seletiva'.")

    colunas_relevantes = {
        'id': 'id_coleta',
        'meta_serialNumber': 'SN',
        'info_date': 'data_coleta',
        'data_peso_entrada': 'peso_entrada_kg',
        'data_peso_saida': 'peso_saida_kg',
        'data_peso_total': 'peso_residuos_kg',
        'data_observacao': 'observacao',
        'data_foto': 'foto_1_url',
        'data_foto2': 'foto_2_url',
        'data_foto3': 'foto_3_url',
        'info_userId': 'operador_id',
        'meta_location_latitude': 'latitude',
        'meta_location_longitude': 'longitude',
        'meta_device_name': 'dispositivo',
        'meta_registrationDate': 'data_registro',
        'mailStatuses_0_pdfFileId':'id_pdf'
    }

    colunas_existentes = {k: v for k, v in colunas_relevantes.items() if k in df.columns}
    df_silver = df[list(colunas_existentes.keys())].rename(columns=colunas_existentes)

    df_silver['data_coleta'] = pd.to_datetime(df_silver['data_coleta'], unit='ms', errors='coerce')
    df_silver['data_registro'] = pd.to_datetime(df_silver['data_registro'], unit='ms', errors='coerce')

    colunas_numericas = ['peso_entrada_kg', 'peso_saida_kg', 'peso_total_kg', 'latitude', 'longitude']
    for col in colunas_numericas:
        if col in df_silver.columns:
            df_silver[col] = pd.to_numeric(df_silver[col], errors='coerce')

    return {"amb": df_silver}

def _transform_irs_coleta_seletiva(df: pd.DataFrame) -> dict:
    """Transforma dados do formulário 'IRS - Coleta Seletiva'."""
    print("  -> Aplicando transformação de 'IRS - Coleta Seletiva'.")

    # Mapeamento de colunas
    colunas_relevantes = {
        'id': 'id_coleta',
        'meta_serialNumber': 'SN',
        'info_date': 'data_coleta',
        'data_peso_entrada': 'peso_entrada_kg',
        'data_peso_saida': 'peso_saida_kg',
        'data_peso_total': 'peso_residuos_kg',
        'data_observacao': 'observacao',
        'data_foto': 'foto_1_url',
        'data_foto2': 'foto_2_url',
        'data_foto3': 'foto_3_url',
        'info_userId': 'operador_id',
        'meta_location_latitude': 'latitude',
        'meta_location_longitude': 'longitude',
        'meta_device_name': 'dispositivo',
        'meta_registrationDate': 'data_registro',
        'mailStatuses_0_pdfFileId':'id_pdf'
    }

    colunas_existentes = {k: v for k, v in colunas_relevantes.items() if k in df.columns}
    df_silver = df[list(colunas_existentes.keys())].rename(columns=colunas_existentes)

    df_silver['data_coleta'] = pd.to_datetime(df_silver['data_coleta'], unit='ms', errors='coerce')
    df_silver['data_registro'] = pd.to_datetime(df_silver['data_registro'], unit='ms', errors='coerce')

    colunas_numericas = ['peso_entrada_kg', 'peso_saida_kg', 'peso_total_kg', 'latitude', 'longitude']
    for col in colunas_numericas:
        if col in df_silver.columns:
            df_silver[col] = pd.to_numeric(df_silver[col], errors='coerce')

    return {"irss": df_silver}


def _transform_irs_coleta_rsd_produtividade(df: pd.DataFrame) -> dict:
    """Transforma dados do formulário 'IRS - Coleta Seletiva'."""
    print("  -> Aplicando transformação de 'IRS - Coleta RSD - Produtividade '.")

    # Mapeamento de colunas
    colunas_relevantes = {
        'id': 'id_coleta',
        'data_buscar_veiculos_id': 'id_veiculo',
        'data_buscar_veiculos_PLACA':'placa',
        'meta_serialNumber': 'SN',
        'data_buscar_veiculos_TIPODEVEICULO':'tipo_veiculo',
        'data_buscar_veiculos_MODELO':'modelo',
        'data_buscar_veiculos_MARCA': 'marca',
        'data_buscar_veiculos_ANODOMODELO':'ano_modelo',
        'info_date': 'data_coleta',
        'data_peso_entrada': 'peso_entrada_kg',
        'data_peso_saida': 'peso_saida_kg',
        'data_peso_total': 'peso_residuos_kg',
        'data_observacao': 'observacao',
        'data_rotaDeColeta': 'rota de coleta',
        'data_nome_motorista': 'motorista',
        'data_coletor': 'coletor',
        'info_userId': 'operador_id',
        'data_buscar_veiculos_lIMITEDACARGAPBTT': 'limit_carg_pbtt',
        'data_buscar_veiculos_lIMITEDACARGAPBTCOMTOLERANCIAT': 'limit_carg_pbtt_com_tol',
        'meta_location_latitude': 'latitude',
        'meta_location_longitude': 'longitude',
        'meta_device_name': 'dispositivo',
        'meta_registrationDate': 'data_registro',
        'data_foto': 'foto_1_url',
        'data_foto2': 'foto_2_url',
        'data_foto3': 'foto_3_url',
        'mailStatuses_0_pdfFileId':'id_pdf'
    }

    colunas_existentes = {k: v for k, v in colunas_relevantes.items() if k in df.columns}
    df_silver = df[list(colunas_existentes.keys())].rename(columns=colunas_existentes)

    df_silver['data_coleta'] = pd.to_datetime(df_silver['data_coleta'], unit='ms', errors='coerce')
    df_silver['data_registro'] = pd.to_datetime(df_silver['data_registro'], unit='ms', errors='coerce')

    colunas_numericas = ['peso_entrada_kg', 'peso_saida_kg', 'peso_total_kg', 'latitude', 'longitude']
    for col in colunas_numericas:
        if col in df_silver.columns:
            df_silver[col] = pd.to_numeric(df_silver[col], errors='coerce')

    return {"irsp": df_silver}

def _transform_ilu_varricao_manual(df: pd.DataFrame) -> dict:
    """Transforma dados do formulário 'ILU - Varrição Manual'."""
    print("  -> Aplicando transformação de 'ILU - Varrição Manual'.")

    colunas_relevantes = {
        'id': 'id_coleta',
        'meta_serialNumber': 'SN',
        'info_date': 'data_varricao',
        'data_localizao_coordinates_latitude': 'latitude',
        'data_localizao_coordinates_longitude': 'longitude',
        'data_localizao_location_road': 'logradouro',
        'data_localizao_location_city': 'cidade',
        'data_localizao_location_postcode': 'cep',
        'data_localizao_location_country': 'pais',
        'data_localizao_formattedValue': 'endereco_completo',
        'data_buscar_REGIAO': 'regiao',
        'data_buscar_id':'id_setor',
        'data_buscar_SETOR': 'setor',
        'data_buscar_LOGRADOURO': 'logradouro_varricao',
        'data_buscar_FREQUENCIA': 'frequencia',
        'data_buscar_EXTENSAOKM': 'extensao_km',
        'data_responsavel_setor': 'responsavel',
        'data_servioExecutado': 'servico_executado',
        'data_observacao': 'observacao',
        'data_foto': 'foto_1_url',
        'data_foto2': 'foto_2_url',
        'data_foto3': 'foto_3_url',
        'info_userId': 'operador_id',
        'meta_location_latitude': 'dispositivo_latitude',
        'meta_location_longitude': 'dispositivo_longitude',
        'meta_device_name': 'dispositivo',
        'meta_registrationDate': 'data_registro',
        'mailStatuses_0_pdfFileId':'id_pdf'
    }

    colunas_existentes = {k: v for k, v in colunas_relevantes.items() if k in df.columns}
    df_silver = df[list(colunas_existentes.keys())].rename(columns=colunas_existentes)

    df_silver['data_varricao'] = pd.to_datetime(df_silver['data_varricao'], unit='ms', errors='coerce')
    df_silver['data_registro'] = pd.to_datetime(df_silver['data_registro'], unit='ms', errors='coerce')

    colunas_numericas = ['latitude', 'longitude', 'extensao_km', 'dispositivo_latitude', 'dispositivo_longitude']
    for col in colunas_numericas:
        if col in df_silver.columns:
            df_silver[col] = pd.to_numeric(df_silver[col], errors='coerce')

    if 'servico_executado' in df_silver.columns:
        df_silver['servico_executado'] = df_silver['servico_executado'].str.upper().map({'SIM': True, 'NÃO': False})

    return {"ilum": df_silver}

def _transform_irs_coleta_veiculo(df: pd.DataFrame) -> dict:
    """Transforma dados do formulário VDR (pesagem)."""
    print("  -> Aplicando transformação de 'IRS - Coleta RSD - Veículo'.")

    colunas_relevantes = {
        'id': 'id_coleta',
        'data_buscar_veiculos_id': 'id_veiculo',
        'data_buscar_veiculos_PLACA':'placa',
        'meta_serialNumber': 'SN',
        'data_buscar_veiculos_TIPODEVEICULO':'tipo_veiculo',
        'data_buscar_veiculos_MODELO':'modelo',
        'data_buscar_veiculos_MARCA': 'marca',
        'data_buscar_veiculos_ANODOMODELO':'ano_modelo',
        'data_buscar_veiculos_lIMITEDACARGAPBTT':'limit_carg_pbtt',
        'data_buscar_veiculos_lIMITEDACARGAPBTCOMTOLERANCIAT':'limit_carg_pbtt_com_tol',
        'data_nome_motorista':'Motorista',
        'data_coletor':'Coletor',
        'info_date': 'data_pesagem',
        'data_peso_entrada': 'peso_entrada_kg',
        'data_peso_saida': 'peso_saida_kg',
        'data_peso_total': 'peso_liquido_kg',
        'data_rotaDeColeta':'rota de coleta',
        'data_conformidade_carga': 'conformidade_carga',
        'data_foto':'foto_1_url',
        'data_foto2':'foto_2_url',
        'data_foto3':'foto_3_url',
        'data_observacao': 'observacao',
        'info_userId': 'operador_id',
        'meta_location_latitude': 'latitude',
        'meta_location_longitude': 'longitude',
        'mailStatuses_0_pdfFileId':'id_pdf'
    }

    colunas_existentes = {k: v for k, v in colunas_relevantes.items() if k in df.columns}
    df_silver = df[list(colunas_existentes.keys())].rename(columns=colunas_existentes)

    df_silver['data_pesagem'] = pd.to_datetime(df_silver['data_pesagem'], unit='ms', errors='coerce')
    colunas_numericas = ['peso_entrada_kg', 'peso_saida_kg', 'peso_liquido_kg', 'latitude', 'longitude']
    for col in colunas_numericas:
        if col in df_silver.columns:
            df_silver[col] = pd.to_numeric(df_silver[col], errors='coerce')

    return {"irsv": df_silver}



def roteador_de_transformacao(df_bronze: pd.DataFrame, nome_arquivo: str) -> dict:
    """
    Identifica o tipo de formulário e chama a função de transformação apropriada.
    """
    nome_arquivo_norm = nome_arquivo.lower().strip()
    print(f"  -> Roteando arquivo: '{nome_arquivo}'")

    if "amb" in nome_arquivo_norm:
        return _transform_ambiental_irs_coleta_seletiva(df_bronze)
    elif "irss" in nome_arquivo_norm:
        return _transform_irs_coleta_seletiva(df_bronze)
    elif "irsrsd" in nome_arquivo_norm:
        return transform_irsrsd_coleta(df_bronze)
    elif "irsv" in nome_arquivo_norm:
        return _transform_irs_coleta_veiculo(df_bronze)
    elif "ilup" in nome_arquivo_norm:
        return _transform_ilu_produtividade(df_bronze)
    elif "irsf" in nome_arquivo_norm:
        return _transform_irs_coleta_rsd_frota(df_bronze)
    elif "ilum" in nome_arquivo_norm: # Corrigido: removido espaço extra no final
        return _transform_ilu_varricao_manual(df_bronze)
    elif "irsp" in nome_arquivo_norm: # Corrigido: removido espaço extra no final
        return _transform_irs_coleta_rsd_produtividade(df_bronze)

    print(f"  -> ATENÇÃO: Nenhuma transformação específica encontrada para '{nome_arquivo}'. Pulando.")
    return {}


def processa_bronze_para_silver(bronze_bucket: str, silver_bucket: str, bronze_prefixo: str, silver_prefixo: str):
    """
    Orquestra o processo de leitura da bronze, transformação e escrita na silver.
    """
    s3_client = boto3.client('s3')
    temp_dir = tempfile.gettempdir()
    print(f"Usando diretório temporário: {temp_dir}")

    try:
        bronze_prefixo_fmt = bronze_prefixo.rstrip('/') + '/'
        print(f"Procurando arquivos em: s3://{bronze_bucket}/{bronze_prefixo_fmt}")

        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bronze_bucket, Prefix=bronze_prefixo_fmt)

        all_files = []
        for page in pages:
            if 'Contents' in page:
                all_files.extend(page['Contents'])

        if not all_files:
            print("Nenhum arquivo encontrado no prefixo da camada bronze.")
            return

        csv_files = [obj['Key'] for obj in all_files if obj['Key'].lower().endswith('.csv') and obj['Size'] > 0]
        print(f"Encontrados {len(csv_files)} arquivos CSV para processar.")

        for file_key in csv_files:
            file_name = os.path.basename(file_key)
            print(f"\n--- Processando arquivo: {file_name} ---")

            local_path = os.path.join(temp_dir, file_name)
            df_bronze = None  # Inicializa para o bloco 'finally'

            try:
                s3_client.download_file(bronze_bucket, file_key, local_path)
                df_bronze = ler_csv_da_bronze(local_path)

                tabelas_silver = roteador_de_transformacao(df_bronze, file_name)

                if not tabelas_silver:
                    continue


                for nome_tabela, df_ou_obj in tabelas_silver.items():
                    if isinstance(df_ou_obj, pd.DataFrame):
                        df_silver = df_ou_obj
                        if not df_silver.empty:
                            csv_buffer = StringIO()
                            df_silver.to_csv(csv_buffer, index=False, encoding='windows-1252', sep='|')

                            silver_key_path = f"{silver_prefixo.rstrip('/')}/{nome_tabela}"
                            silver_file_name = f"{os.path.splitext(file_name)[0]}.csv"
                            silver_key = f"{silver_key_path}/{silver_file_name}"

                            s3_client.put_object(Bucket=silver_bucket, Key=silver_key, Body=csv_buffer.getvalue())
                            print(
                                f"  -> Tabela '{nome_tabela}' salva em s3://{silver_bucket}/{silver_key} com {len(df_silver)} registros.")
                        else:
                            print(f"  -> Tabela '{nome_tabela}' estava vazia. Nenhum arquivo foi salvo.")
                    else:
                        print(f"  -> Objeto '{nome_tabela}' não é um DataFrame e será ignorado.")


            except KeyError as e:
                print(f"  -> ERRO DE CHAVE (Coluna não encontrada): {e}")
                print("  -> Verifique o mapeamento na função de transformação.")
                if df_bronze is not None:
                    print(f"  -> COLUNAS DISPONÍVEIS: {list(df_bronze.columns)}")

            except Exception as e:
                print(f"  -> ERRO FATAL ao processar o arquivo {file_name}: {e}")
            finally:
                if os.path.exists(local_path):
                    os.remove(local_path)

    except Exception as e:
        print(f"Erro geral no processo: {e}")


if __name__ == "__main__":
    BRONZE_BUCKET = "dev-houer-us-east-1-bronze-zone"
    SILVER_BUCKET = "dev-houer-us-east-1-silver-zone"
    BRONZE_PREFIXO = "project-bubbleman/moreapp/submissions/"
    SILVER_PREFIXO = "project-bubbleman/moreapp/submissions/"

    processa_bronze_para_silver(BRONZE_BUCKET, SILVER_BUCKET, BRONZE_PREFIXO, SILVER_PREFIXO)
