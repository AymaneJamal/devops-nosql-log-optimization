FROM --platform=linux/arm64 docker.elastic.co/logstash/logstash:7.17.0

# Install MongoDB output plugin
RUN bin/logstash-plugin install logstash-output-mongodb

# Create log4j2.properties to avoid warnings
RUN echo "status = error\n\
appender.console.type = Console\n\
appender.console.name = console\n\
appender.console.layout.type = PatternLayout\n\
appender.console.layout.pattern = [%d{ISO8601}][%-5p][%-25c{1.}] %marker%m%n\n\
rootLogger.level = info\n\
rootLogger.appenderRef.console.ref = console" > /usr/share/logstash/config/log4j2.properties

# Créer un fichier logstash.yml modifiable au lieu de modifier celui existant
RUN echo "http.host: \"0.0.0.0\"\n\
xpack.monitoring.elasticsearch.hosts: [\"http://elasticsearch:9200\"]\n\
path.config: /usr/share/logstash/pipeline\n\
pipeline.workers: 2\n\
pipeline.batch.size: 125\n\
pipeline.batch.delay: 50\n\
pipeline.ecs_compatibility: disabled" > /usr/share/logstash/config/logstash.yml.new \
    && mv /usr/share/logstash/config/logstash.yml.new /usr/share/logstash/config/logstash.yml

# Configuration pour la santé du conteneur
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:9600 || exit 1