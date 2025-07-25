# Use an official Apache Spark runtime as a parent image
FROM apache/spark:3.5.0

# Set the working directory
WORKDIR /opt/spark

# Download Delta Lake jar
RUN wget https://repo1.maven.org/maven2/io/delta/delta-core_2.12/1.0.0/delta-core_2.12-1.0.0.jar -P /opt/spark/jars/
RUN wget https://repo1.maven.org/maven2/org/apache/poi/poi/4.1.2/poi-4.1.2.jar -P /opt/spark/jars/
RUN wget https://repo1.maven.org/maven2/org/apache/poi/poi-ooxml/4.1.2/poi-ooxml-4.1.2.jar -P /opt/spark/jars/
RUN wget https://repo1.maven.org/maven2/org/apache/poi/poi-ooxml-schemas/4.1.2/poi-ooxml-schemas-4.1.2.jar -P /opt/spark/jars/
RUN wget https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.2.0/hadoop-aws-3.2.0.jar -P /opt/spark/jars/
#RUN wget https://repo1.maven.org/maven2/com/github/crealytics/spark/excel_2.12/0.13.8/spark-excel_2.12-0.13.8.jar -P /opt/spark/jars/

# TODO Trazer as dependencias do delta_cor e do hadoop_aws pra cá

# Add Delta Lake jar as a dependency
ENV SPARK_EXTRA_CLASSPATH=/opt/spark/jars/delta-core_2.12-1.0.0.jar:/opt/spark/jars/poi-4.1.2.jar:/opt/spark/jars/poi-ooxml-4.1.2.jar:/opt/spark/jars/poi-ooxml-schemas-4.1.2.jar:/opt/spark/jars/hadoop-aws-3.2.0.jar

# Copy the custom entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Switch to root user to execute the chmod command
USER root

# Make the script executable
RUN chmod +x /usr/local/bin/entrypoint.sh

# Switch back to the original user
USER 185

# Expose Spark master and worker web UI ports
EXPOSE 8080 7077 8081 8082

# Start the Spark shell
#CMD ["bin/spark-shell"]
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]