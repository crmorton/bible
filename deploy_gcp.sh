#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

PROJECT_ID="kerygma-didache-logos"
IMAGE_NAME="bible-api-prod"
# Target regions for low latency across Globe
# REGIONS=("us-central1" "europe-west4" "asia-northeast1" "australia-southeast1")
REGIONS=("us-central1")

echo "======================================================"
echo " Building and Deploying Bible API to Google Cloud Run "
echo "======================================================"

echo "[1/2] Submitting build to Google Cloud Build..."
# Build the image using the production Dockerfile
# Use cloudbuild.yaml since it cleanly handles custom Dockerfile names
gcloud builds submit --config cloudbuild.yaml --project ${PROJECT_ID} .

echo "[2/2] Deploying to Cloud Run in multiple regions..."
for REGION in "${REGIONS[@]}"
do
    SERVICE_NAME="bible-api-${REGION}"
    echo "------------------------------------------------------"
    echo "Deploying to ${REGION} as service ${SERVICE_NAME}..."
    gcloud run deploy ${SERVICE_NAME} \
      --image gcr.io/${PROJECT_ID}/${IMAGE_NAME} \
      --region ${REGION} \
      --allow-unauthenticated \
      --project ${PROJECT_ID} \
      --memory 512Mi \
      --cpu 1 \
      --min-instances 0 \
      --max-instances 10
done

echo "======================================================"
echo " Deployment Complete! "
echo "======================================================"
echo "Note: Your regional services are now live. The next step is"
echo "to configure a Cloudflare Load Balancer to route traffic"
echo "to the nearest region and enable Edge Caching."
