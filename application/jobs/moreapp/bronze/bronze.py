import pandas as pd
import json
from src.phynfra.phynfra.aws.s3 import S3
import os
from io import StringIO

### GLOBOAL VARS ###
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
api_key = os.environ.get("MOREAPP_API_KEY")
customerId = os.environ.get("MOREAPP_API_CUSTOMER")
moreapp_forms = {
				"IRS - Coleta RSD - Produtividade": "66e331f4c270fb1275d502fe",
				"IRS - Coleta RSD - Veículo": "66e452554ff3e8584643f096",
				"IRS - Coleta RSD - Frota": "66e33424e4bb966929ce5348",
				"IRS - Coleta Seletiva": "66e335a68410676c7282034b",
				"ILU - Varrição Manual": "66e3368b8410676c72820358",
				"ILU - Produtividade": "66e43cc58410676c72820a7a",
				"Ambiental - IRS - Coleta Seletiva": "67fe71ace4ea1401e28ea185"
            }

def flatten_json(y):
    """
    Flatten a nested JSON object into a single-level dictionary.
    """
    def flatten(x, name=''):
        """
        Recursive function to flatten the JSON object.
        """
        if isinstance(x, dict):
            for k, v in x.items():
                flatten(v, name + k + '_')
        elif isinstance(x, list):
            for i, v in enumerate(x):
                flatten(v, name + str(i) + '_')
        else:
            out[name[:-1]] = x

    out = {}
    flatten(y)
    return out

def flatten_json_list(json_data, keys):
    """
    Flatten a list of nested JSON objects.
    """
    return [flatten_json(item) for item in select_json_parts(json_data, keys)]

def select_json_parts(json_data, keys):
    """
    Select specific parts from the json that you want to flatten
    """
    selected_data = []
    for item in json_data:
        selected_item = {key: item.get(key, None) for key in keys}
        selected_data.append(selected_item)
    return selected_data

keys_to_select = ['id', 'data', 'info', 'meta', 'mailStatuses']

def main():
    for key, value in moreapp_forms.items():
        try:
            s3_bucket = "dev-houer-us-east-1-landing-zone"
            s3_id_key = f"project-bubbleman/moreapp/submissions/{key}/{key}-form_id-{value}.json"
            s3_client = S3(region="us-east-1", accessKey=AWS_ACCESS_KEY, secretKey=AWS_SECRET_ACCESS_KEY)
            json_data = s3_client.read(bucket=s3_bucket, keyPrefix=s3_id_key)
            data = json.loads(json_data)
            flattened_json = flatten_json_list(data, keys_to_select)
            df = pd.DataFrame(flattened_json)
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            s3_bucket = "dev-houer-us-east-1-bronze-zone"
            s3_id_key = f"project-bubbleman/moreapp/submissions/{key}/{key}-form_id-{value}.csv"
            s3_client.write(bucket=s3_bucket, payload=csv_buffer.getvalue(), keyPrefix=s3_id_key)
        except Exception as e:
            print(e)

main()
