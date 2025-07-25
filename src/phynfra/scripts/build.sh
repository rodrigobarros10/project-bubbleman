#!/bin/bash

cd ..

rm -fr venv
rm -fr phynfra.egg-info
rm poetry.lock
rm ./dist/*.whl
rm ./dist/*.gz

python3 -m virtualenv venv

source venv/bin/activate

pip install poetry
poetry install
poetry build

#git push origin master
