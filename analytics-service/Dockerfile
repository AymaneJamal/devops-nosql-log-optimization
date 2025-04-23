FROM maven:3.9.9-eclipse-temurin-21 AS builder

WORKDIR /app

COPY pom.xml .

# Conserver osx-aarch_64 ou modifier pour linux-aarch_64 si nécessaire
RUN sed -i 's/osx-aarch_64/linux-aarch_64/g' pom.xml

RUN mvn dependency:go-offline -B

COPY src ./src

RUN mvn clean package

FROM --platform=linux/arm64 openjdk:21-jdk AS runner

WORKDIR /app

COPY --from=builder ./app/target/analytics-service-0.0.1-SNAPSHOT.jar ./app.jar

EXPOSE 4002

ENTRYPOINT ["java", "-jar", "app.jar"]