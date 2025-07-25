#!/bin/bash
docker build --no-cache -t spark-phynfra:latest -f spark.Dockerfile .

# pip install git+https://github.com/jkbr/httpie.git#egg=httpie
# pip install git+https://github.com/tangentlabs/django-oscar-paypal.git@issue/34/oscar-0.6#egg=django-oscar-paypal