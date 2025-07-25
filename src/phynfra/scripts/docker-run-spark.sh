#!/bin/bash

docker run --rm --name spark --network host -p 8080:8080 -p 8081:8081 -p 7077:7077 -p 8082:8082 -d spark-phynfra
