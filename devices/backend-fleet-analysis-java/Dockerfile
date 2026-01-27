FROM maven:3.9.6-eclipse-temurin-21 AS build

WORKDIR /workspace
COPY pom.xml .
COPY src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21-jre

ARG PAYARA_MICRO_VERSION=6.2024.2
WORKDIR /opt/payara
ADD https://repo1.maven.org/maven2/fish/payara/extras/payara-micro/${PAYARA_MICRO_VERSION}/payara-micro-${PAYARA_MICRO_VERSION}.jar /opt/payara/payara-micro.jar

COPY --from=build /workspace/target/fleet-analysis-backend.war /opt/payara/fleet-analysis-backend.war

EXPOSE 8080
ENTRYPOINT ["java","-jar","/opt/payara/payara-micro.jar","--deploy","/opt/payara/fleet-analysis-backend.war","--contextRoot","/fleet-analysis"]
