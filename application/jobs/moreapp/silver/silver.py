import pandas as pd
from src.phynfra.phynfra.aws.s3 import S3
import os
from io import StringIO
import requests
import boto3

### GLOBOAL VARS ###
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
api_key = os.environ.get("MOREAPP_API_KEY")
customerid = os.environ.get("MOREAPP_API_CUSTOMER")
moreapp_forms = {
           		 "IRS - Coleta RSD - Produtividade": "66e331f4c270fb1275d502fe",
				"IRS - Coleta RSD - Veículo": "66e452554ff3e8584643f096",
				"IRS - Coleta RSD - Frota": "66e33424e4bb966929ce5348",
				"IRS - Coleta Seletiva": "66e335a68410676c7282034b",
				"ILU - Varrição Manual": "66e3368b8410676c72820358",
				"ILU - Produtividade": "66e43cc58410676c72820a7a",
				"Ambiental - IRS - Coleta Seletiva": "67fe71ace4ea1401e28ea185"
            }
project = os.environ.get("PYTHONPATH").split("\\")[-1]
moreapp_files = ["images", "videos", "pdfs"]
### END GLOBAL VARS ###

def download_files_from_moreapp(dataframe: pd.DataFrame, moreapp_form: str, file_type: str):
    '''
    Download files that are not available at S3
    file_type -> str: must be images, videos or pdfs
    '''
    if file_type == "images":
        images_list = send_list_of_files(dataframe=dataframe, moreapp_form=moreapp_form, file_type=file_type)
        for file in images_list:
            url = f"https://api.moreapp.com/api/v1.0/customers/{customerid}/registrationFile/{file}/download"

            headers = {
                "Accept": "*/*",
                "X-Api-Key": api_key
            }
            response = requests.get(url, headers=headers)

            if not os.path.exists(f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}'):
                os.makedirs(f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}')

            filepath = f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}/{file}.png'
            with open(f'{filepath}', 'wb') as file:
                file.write(response.content)

        send_file_to_s3(moreapp_form=moreapp_form, file_type=file_type)

    elif file_type == "videos":
        videos_list = send_list_of_files(dataframe=dataframe, moreapp_form=moreapp_form, file_type=file_type)
        for file in videos_list:
            url = f"https://api.moreapp.com/api/v1.0/customers/{customerid}/registrationFile/{file}/download"

            headers = {
                "Accept": "*/*",
                "X-Api-Key": api_key
            }
            response = requests.get(url, headers=headers)

            if not os.path.exists(f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}'):
                os.makedirs(f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}')

            filepath = f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}/{file}.mp4'
            with open(f'{filepath}', 'wb') as file:
                file.write(response.content)

        send_file_to_s3(moreapp_form=moreapp_form, file_type=file_type)

    else:
        pdfs_list = send_list_of_files(dataframe=dataframe, moreapp_form=moreapp_form, file_type=file_type)
        for file in pdfs_list:
            url = f"https://api.moreapp.com/api/v1.0/customers/{customerid}/registrationFile/{file}/download"

            headers = {
                "Accept": "*/*",
                "X-Api-Key": api_key
            }
            response = requests.get(url, headers=headers)

            if not os.path.exists(f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}'):
                os.makedirs(f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}')

            filepath = f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}/{file}.pdf'
            with open(f'{filepath}', 'wb') as file:
                file.write(response.content)

        send_file_to_s3(moreapp_form=moreapp_form, file_type=file_type)

def scan_files_already_in_s3_bucket(moreapp_form: str, file_type: str) -> list:
    if file_type == "images":
        try:
            s3_client = boto3.client('s3', region_name = 'us-east-1', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            s3_bucket = "houer-vi-publico"
            prefix = f"{project}/moreapp/{file_type}/{moreapp_form}"
            paginator = s3_client.get_paginator('list_objects_v2')
            operation_parameters = {'Bucket': s3_bucket,
                                    'Prefix': prefix}
            iterador = paginator.paginate(**operation_parameters)
            list_images_string = []
            for page in iterador:
                output = page.get('Contents', [])
                for object in output:
                    list_images_string.append(str(str(object['Key']).split(f'{moreapp_form}/', 1)[1]).split(".")[0])
            return list_images_string
        except Exception:
            return []
    elif file_type=="videos":
        try:
            s3_client = boto3.client('s3', region_name = 'us-east-1', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            s3_bucket = "houer-vi-publico"
            prefix = f"{project}/moreapp/{file_type}/{moreapp_form}"
            paginator = s3_client.get_paginator('list_objects_v2')
            operation_parameters = {'Bucket': s3_bucket,
                                    'Prefix': prefix}
            iterador = paginator.paginate(**operation_parameters)
            list_videos_string = []
            for page in iterador:
                output = page.get('Contents', [])
                for object in output:
                    list_videos_string.append(str(str(object['Key']).split(f'{moreapp_form}/', 1)[1]).split(".")[0])
            return list_videos_string
        except Exception:
            return []
    else:
        try:
            s3_client = boto3.client('s3', region_name = 'us-east-1', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            s3_bucket = "houer-vi-publico"
            prefix = f"{project}/moreapp/{file_type}/{moreapp_form}"
            paginator = s3_client.get_paginator('list_objects_v2')
            operation_parameters = {'Bucket': s3_bucket,
                                    'Prefix': prefix}
            iterador = paginator.paginate(**operation_parameters)
            list_pdfs_string = []
            for page in iterador:
                output = page.get('Contents', [])
                for object in output:
                    list_pdfs_string.append(str(str(object['Key']).split(f'{moreapp_form}/', 1)[1]).split(".")[0])
            return list_pdfs_string
        except Exception:
            return []

def send_list_of_files(dataframe: pd.DataFrame, moreapp_form: str, file_type: str) -> list:
    if file_type == "images":
        # Procura todas as colunas que possuem photo, foto ou assinatura no nome
        key_file_1 = "foto"
        key_file_2 = "photo"
        key_file_3 = "assinatura"
        key_file_4 = "registrodaevidcia"
        images_columns = [column for column in dataframe.columns if key_file_1 in str.lower(column) or key_file_2 in str.lower(column) or key_file_3 in str.lower(column) or key_file_4 in str.lower(column)]
        # Tira aquelas que tiveram o path corrompido ou nan
        df_foto = dataframe[images_columns]
        all_fotos = []
        for column in df_foto.columns:
            for row in df_foto[column]:
                if pd.isna(row):
                    pass
                else:
                    all_fotos.append(str(row).split('gridfs://registrationFiles/', 1)[1])

        # Aqui é um verificador para saber se a imagem já está no Bucket
        images_already_in_bucket = scan_files_already_in_s3_bucket(moreapp_form=moreapp_form, file_type=file_type)

        # Comparar quais imagens ainda não estão no bucket
        images_to_download = list(set(all_fotos) - set(images_already_in_bucket))
        return images_to_download

    elif file_type=="videos":
        key_file_1 = "video"
        videos_columns = [column for column in dataframe.columns if key_file_1 in str.lower(column)]
        # Tira aquelas que tiveram o path corrompido ou nan
        df_video = dataframe[videos_columns]
        all_videos = []
        for column in df_video.columns:
            for row in df_video[column]:
                if pd.isna(row):
                    pass
                else:
                    all_videos.append(str(row).split('gridfs://registrationFiles/', 1)[1])

        # Aqui é um verificador para saber se o vídeo já está no Bucket
        videos_already_in_bucket = scan_files_already_in_s3_bucket(moreapp_form=moreapp_form, file_type=file_type)

        # Comparar quais vídeos ainda não estão no bucket
        videos_to_download = list(set(all_videos) - set(videos_already_in_bucket))
        return videos_to_download

    else:
    # Procura todas as colunas que possuem pdfFileId no nome
        key_file_1 = "pdfFileId"
        pdf_columns = [column for column in dataframe.columns if str.lower(key_file_1) in str.lower(column)]
        # Tira aquelas que tiveram o path corrompido ou nan
        df_pdf = dataframe[pdf_columns]
        all_pdfs = []
        for column in df_pdf.columns:
            for row in df_pdf[column]:
                if pd.isna(row):
                    pass
                else:
                    all_pdfs.append(row)

        # Aqui é um verificador para saber se o PDF já está no Bucket
        pdf_already_in_bucket = scan_files_already_in_s3_bucket(moreapp_form=moreapp_form, file_type=file_type)

        # Comparar quais PDFs ainda não estão no bucket
        pdfs_to_download = list(set(all_pdfs) - set(pdf_already_in_bucket))
        return pdfs_to_download

def send_file_to_s3(moreapp_form: str, file_type: str):
    if file_type=="images":
        try:
            filenames = os.listdir(f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}')
            for file in filenames:
                filepath = f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}/{file}'
                handler = open(filepath, 'rb')
                payload = handler.read()
                s3_bucket = "houer-vi-publico"
                prefix = f"{project}/moreapp/{file_type}/{moreapp_form}/{file}"
                s3_client = S3(region="us-east-1", accessKey=AWS_ACCESS_KEY, secretKey=AWS_SECRET_ACCESS_KEY)
                s3_client.write(bucket=s3_bucket, payload=payload, contentType = "image/png", keyPrefix=prefix)
            print(f"{file_type} has been uploaded to houer-vi-publico/{project}/moreapp/{file_type}/{moreapp_form}")
        except:
            print(f"Can't find path for './application/jobs/moreapp/files/{file_type}/{moreapp_form}'")
    elif file_type=="videos":
        try:
            filenames = os.listdir(f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}')
            for file in filenames:
                filepath = f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}/{file}'
                handler = open(filepath, 'rb')
                payload = handler.read()
                s3_bucket = "houer-vi-publico"
                prefix = f"{project}/moreapp/{file_type}/{moreapp_form}/{file}"
                s3_client = S3(region="us-east-1", accessKey=AWS_ACCESS_KEY, secretKey=AWS_SECRET_ACCESS_KEY)
                s3_client.write(bucket=s3_bucket, payload=payload, contentType = "video/mp4", keyPrefix=prefix)
            print(f"{file_type} has been uploaded to houer-vi-publico/{project}/moreapp/{file_type}/{moreapp_form}")
        except:
            print(f"Can't find path for './application/jobs/moreapp/files/{file_type}/{moreapp_form}'")
    else:
        try:
            filenames = os.listdir(f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}')
            for file in filenames:
                filepath = f'./application/jobs/moreapp/files/{file_type}/{moreapp_form}/{file}'
                handler = open(filepath, 'rb')
                payload = handler.read()
                s3_bucket = "houer-vi-publico"
                prefix = f"{project}/moreapp/{file_type}/{moreapp_form}/{file}"
                s3_client = S3(region="us-east-1", accessKey=AWS_ACCESS_KEY, secretKey=AWS_SECRET_ACCESS_KEY)
                s3_client.write(bucket=s3_bucket, payload=payload, contentType = "application/pdf", keyPrefix=prefix)
            print(f"{file_type} has been uploaded to houer-vi-publico/{project}/moreapp/pdfs/{moreapp_form}")
        except:
            print(f"Can't find path for './application/jobs/moreapp/files/{file_type}/{moreapp_form}'")

def main():
    for key, value in moreapp_forms.items():
        try:
            s3_bucket = "dev-houer-us-east-1-bronze-zone"
            s3_id_key = f"{project}/moreapp/submissions/{key}/{key}-form_id-{value}.csv"
            s3_client = S3(region="us-east-1", accessKey=AWS_ACCESS_KEY, secretKey=AWS_SECRET_ACCESS_KEY)
            csv_data = s3_client.read(bucket=s3_bucket, keyPrefix=s3_id_key)
            df = pd.DataFrame(pd.read_csv(StringIO(csv_data)))
            columns_to_select = ["data_", "pdfFileId"]
            selected_columns = []
            for column in df.columns:
                for column_to_select in columns_to_select:
                    if column_to_select in column:
                        selected_columns.append(column)
            selected_columns.append("id")
            selected_columns.append("info_date")
            selected_columns.append("meta_serialNumber")
            df = df[selected_columns]
            df.rename(columns={"id": "moreapp_submission_id"}, inplace=True)
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            s3_bucket = "dev-houer-us-east-1-silver-zone"
            s3_id_key = f"{project}/moreapp/submissions/{key}/{key}.csv"
            s3_client.write(bucket=s3_bucket, payload=csv_buffer.getvalue(), keyPrefix=s3_id_key)
            for file_type in moreapp_files:
                download_files_from_moreapp(dataframe=df, moreapp_form=key, file_type=file_type)
        except Exception as e:
            print(e)

main()
