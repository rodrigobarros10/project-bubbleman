#!/bin/bash

# Call "run" with .env envvar
python -m phynfra --command run --configuration /path/to/.env --module phynfra.tester.somefunction

# Call "run" directly from os.environ
python -m phynfra --command run --module phynfra.tester.roda

# Call "create" to create the directory structure in the destination argument - Destination must exists
python -m phynfra --command create --configuration /path/to/.env --destination /fullpath/to/destination

# Perform an "ETL" directly using Apache Spark
python -m phynfra --command transform --configuration /path/to/.env --source protocol://path/to/file.extension --target protocol://path/to/file.extension
