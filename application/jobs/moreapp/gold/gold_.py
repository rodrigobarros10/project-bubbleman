import pandas as pd
from src.phynfra.phynfra.aws.s3 import S3
import os
from io import StringIO, BytesIO
import boto3

### GLOBOAL VARS ###
# REMOVIDO: As credenciais não são mais lidas explicitamente no script.
# O boto3 as encontrará automaticamente nas variáveis de ambiente.
# AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
# AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

api_key = os.environ.get("MOREAPP_API_KEY")
customerid = os.environ.get("MOREAPP_API_CUSTOMER")
moreapp_forms = {
	"irsp": "66c8d998e5a2cf14ff76cdcd",
	"irsv": "66e3337fe4bb966929ce5346",
	"irsf": "66e33424e4bb966929ce5348",
	# "irss": "66e335a68410676c7282034b",
	"ilum": "66e3368b8410676c72820358",
	"ilup": "66e43cc58410676c72820a7a",
}
project = os.environ.get("PYTHONPATH").split("\\")[-1]
moreapp_files = ["images", "videos", "pdfs"]


### END GLOBAL VARS ###

def scan_content_in_s3_bucket(s3_client: boto3.client, content: str, moreapp_form: str) -> list:
	"""Scans for content files in the public S3 bucket."""
	try:
		s3_bucket = "houer-vi-publico"
		prefix = f"{project}/moreapp/{content}/{moreapp_form}"
		paginator = s3_client.get_paginator('list_objects_v2')
		pages = paginator.paginate(Bucket=s3_bucket, Prefix=prefix)

		content_keys = []
		for page in pages:
			for obj in page.get('Contents', []):
				file_name = obj['Key'].split(f'{moreapp_form}/', 1)[1]
				content_keys.append(file_name)
		return content_keys
	except Exception as e:
		print(f"Error scanning bucket for {content}/{moreapp_form}: {e}")
		return []


def generate_final_df(s3_phynfra_client: S3, moreapp_form: str) -> pd.DataFrame:
	"""Reads CSV from silver zone, transforms it, and writes as Parquet to gold zone."""
	s3_bucket_silver = "dev-houer-us-east-1-silver-zone"
	s3_key_silver = f"{project}/moreapp/submissions/{moreapp_form}/{moreapp_form}.csv"

	print(f"Reading CSV for form '{moreapp_form}' from silver zone...")
	csv_data = s3_phynfra_client.read(bucket=s3_bucket_silver, keyPrefix=s3_key_silver)
	df = pd.read_csv(StringIO(csv_data))

	columns_to_keep = [col for col in df.columns if "pdfFileId" not in col]
	if "mailStatuses_0_pdfFileId" in df.columns:
		columns_to_keep.append("mailStatuses_0_pdfFileId")

	df = df[columns_to_keep]
	df.rename(columns={"mailStatuses_0_pdfFileId": "pdf_file_id"}, inplace=True)

	s3_bucket_gold = "dev-houer-us-east-1-gold-zone"
	s3_key_gold = f"{project}/moreapp/submissions/{moreapp_form}/{moreapp_form}"

	print(f"Writing Parquet for form '{moreapp_form}' to gold zone...")
	s3_phynfra_client.write(bucket=s3_bucket_gold, payload=df.to_parquet(), keyPrefix=s3_key_gold)

	return df


def generate_df_with_links(s3_boto_client: boto3.client, content: str, moreapp_form: str) -> pd.DataFrame:
	"""Generates a DataFrame with public links to media files."""
	s3_bucket_gold = "dev-houer-us-east-1-gold-zone"
	s3_key_gold = f"{project}/moreapp/submissions/{moreapp_form}/{moreapp_form}"

	try:
		obj = s3_boto_client.get_object(Bucket=s3_bucket_gold, Key=s3_key_gold)
		df = pd.read_parquet(BytesIO(obj['Body'].read()))
	except s3_boto_client.exceptions.NoSuchKey:
		print(f"Warning: Parquet file not found for form '{moreapp_form}'. Skipping link generation.")
		return None

	df_media = pd.DataFrame()
	id_col, val_col, key_words, extension = None, None, [], None

	if content == "images":
		key_words = ["foto", "photo", "assinatura", "registrodaevidcia"]
		id_col, val_col, extension = "id_foto", "codigo_foto", ".png"
	elif content == "videos":
		key_words = ["video"]
		id_col, val_col, extension = "id_video", "codigo_video", ".mp4"
	elif content == "pdfs":
		key_words = ["pdf_file_id"]
		id_col, val_col, extension = "id_pdf", "codigo_pdf", ".pdf"

	media_columns = [col for col in df.columns if any(kw in col.lower() for kw in key_words)]
	if not media_columns and content != 'pdfs':
		return None

	if content == 'pdfs':
		df_media = df[["moreapp_submission_id", "pdf_file_id"]].copy()
		df_media.rename(columns={"pdf_file_id": val_col}, inplace=True)
	else:
		media_columns.append("moreapp_submission_id")
		df_filtered = df[media_columns]
		df_media = pd.melt(df_filtered, id_vars=['moreapp_submission_id'], var_name="source_column", value_name=val_col)

	df_media.dropna(subset=[val_col], inplace=True)
	if df_media.empty:
		return None

	if content in ["images", "videos"]:
		df_media[id_col] = df_media[val_col].apply(
			lambda x: str(x).split("gridfs://registrationFiles/")[1] if "gridfs" in str(x) else None)
	else:  # PDFs
		df_media[id_col] = df_media[val_col]

	df_media.dropna(subset=[id_col], inplace=True)

	files_in_s3 = scan_content_in_s3_bucket(s3_boto_client, content=content, moreapp_form=moreapp_form)
	if not files_in_s3:
		return None

	links = []
	for file_path in files_in_s3:
		file_id = file_path.rsplit(extension, 1)[0]
		url = f"https://houer-vi-publico.s3.amazonaws.com/{project}/moreapp/{content}/{moreapp_form}/{file_path}"
		links.append({"file_id": file_id, "url": url})

	df_links = pd.DataFrame(links)

	df_final = df_media.merge(df_links, left_on=id_col, right_on='file_id')
	df_final = df_final[["moreapp_submission_id", id_col, "url"]]
	df_final.rename(columns={"url": "url_presigned", id_col: f"id_{content[:-1]}"}, inplace=True)
	df_final["formulario_moreapp"] = moreapp_form

	return df_final


def main():
	"""Main ETL orchestration function."""
	# ALTERADO: Removida a passagem explícita de credenciais.
	# O boto3 usará as variáveis de ambiente (AWS_ACCESS_KEY_ID, etc.).
	# É assumido que a classe S3 também usa boto3 internamente e se beneficiará disso.
	s3_phynfra_client = S3(region="us-east-1")
	s3_boto_client = boto3.client('s3', region_name='us-east-1')

	print("--- Starting Stage 1: CSV to Parquet Conversion ---")
	for form_name, form_id in moreapp_forms.items():
		try:
			generate_final_df(s3_phynfra_client, moreapp_form=form_name)
		except Exception as e:
			print(f"Failed to process form '{form_name}'. Error: {e}")
	print("--- Stage 1 Complete ---\n")

	print("--- Starting Stage 2: Media Link Generation ---")
	for content_type in moreapp_files:
		print(f"\nProcessing content type: '{content_type}'")
		all_urls_for_content_type = []
		for form_name, form_id in moreapp_forms.items():
			try:
				print(f"  Generating links for form '{form_name}'...")
				df_links = generate_df_with_links(s3_boto_client, content=content_type, moreapp_form=form_name)
				if df_links is not None and not df_links.empty:
					all_urls_for_content_type.append(df_links)
			except Exception as e:
				print(f"  Failed to generate links for '{form_name}' and content '{content_type}'. Error: {e}")

		if all_urls_for_content_type:
			final_df = pd.concat(all_urls_for_content_type, ignore_index=True)

			s3_bucket = "dev-houer-us-east-1-gold-zone"
			s3_key = f"{project}/moreapp/submissions/{content_type}/{content_type}"
			print(f"Writing consolidated '{content_type}' links to {s3_bucket}/{s3_key}")
			s3_phynfra_client.write(bucket=s3_bucket, payload=final_df.to_parquet(), keyPrefix=s3_key)
		else:
			print(f"No data found for content type '{content_type}' across all forms.")
	print("\n--- Stage 2 Complete ---")
	print("ETL process finished.")


if __name__ == "__main__":
	main()
