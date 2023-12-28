#!/bin/bash
ENVIRONMENT=$1

echo $ENVIRONMENT

source .autodevops/service.properties

# cz bump -ch

SERVICE_VERSION=$(cz version -p)
IMAGE_NAME=shkedia-photo-${COMPONENT_NAME}-service:${SERVICE_VERSION}
IMAGE_FULL_NAME=public.ecr.aws/q2n5r5e8/project-shkedia/${IMAGE_NAME}

echo BUILD IMAGE $IMAGE_FULL_NAME
# docker build . -t ${IMAGE_FULL_NAME}

ENVIRONMENT=dev
DEPLOYMENT_ENV=.local/${COMPONENT_NAME}_service_${ENVIRONMENT}.env

export ${COMPONENT_NAME^^}_SERVICE_VERSION=$SERVICE_VERSION

docker compose --env-file ${DEPLOYMENT_ENV} up -d