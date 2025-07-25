#!/bin/bash

# Start the Spark standalone master
/opt/spark/sbin/start-master.sh -h 0.0.0.0

# Start the Spark standalone worker
/opt/spark/sbin/start-worker.sh spark://localhost:7077 -p 8081 -m 2048M

# Keep the container running
tail -f /dev/null