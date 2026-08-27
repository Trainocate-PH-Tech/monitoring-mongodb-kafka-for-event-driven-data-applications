FROM alpine:3.22 AS connector

ARG MONGO_CONNECTOR_VERSION=3.0.0
ARG MONGO_CONNECTOR_SHA256=0a59a4ecea195cb6e7af6bb79463dbaf1d6a51c6bae72beca44c54cb5e8e15f7
RUN wget -q -O /mongo-kafka-connect-all.jar \
      "https://repo1.maven.org/maven2/org/mongodb/kafka/mongo-kafka-connect/${MONGO_CONNECTOR_VERSION}/mongo-kafka-connect-${MONGO_CONNECTOR_VERSION}-all.jar" \
    && echo "${MONGO_CONNECTOR_SHA256}  /mongo-kafka-connect-all.jar" | sha256sum -c -

FROM apache/kafka:4.3.1
USER root
RUN mkdir -p /opt/kafka/plugins/mongodb
COPY --from=connector /mongo-kafka-connect-all.jar /opt/kafka/plugins/mongodb/
COPY config/connect-distributed.properties /opt/kafka/config/workshop-connect-distributed.properties
USER appuser

CMD ["/opt/kafka/bin/connect-distributed.sh", "/opt/kafka/config/workshop-connect-distributed.properties"]
