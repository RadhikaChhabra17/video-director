#!/usr/bin/env bash
set -euo pipefail

# ==============================================================
# Google Cloud Run Deployment Script
# Creative Intelligence Studio (Vertex AI + Cloud Run + GCP Storage)
# ==============================================================

SERVICE_NAME="${SERVICE_NAME:-content-studio}"
REGION="${REGION:-us-central1}"
GCP_PROJECT="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo "")}"

# Fallback default project ID if not set via environment or gcloud config
if [ -z "$GCP_PROJECT" ]; then
    GCP_PROJECT="aibuildercup2026"
fi

echo "=========================================================="
echo " Configuration:"
echo " Project: $GCP_PROJECT"
echo " Region:  $REGION"
echo " Service: $SERVICE_NAME"
echo "=========================================================="

# 1. Enable Required Google Cloud APIs
echo ""
echo "--> Enabling Vertex AI, Cloud Run, Artifact Registry, Firestore, and Storage APIs..."
gcloud services enable \
    aiplatform.googleapis.com \
    firestore.googleapis.com \
    storage.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    artifactregistry.googleapis.com \
    --project "$GCP_PROJECT"

# 2. Grant IAM Roles to Cloud Run Default Service Account
echo ""
echo "--> Configuring IAM permissions for Cloud Run service account..."
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format="value(projectNumber)")
DEFAULT_COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant Vertex AI User
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
    --member="serviceAccount:${DEFAULT_COMPUTE_SA}" \
    --role="roles/aiplatform.user" >/dev/null 2>&1 || true

# Grant Firestore Datastore User
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
    --member="serviceAccount:${DEFAULT_COMPUTE_SA}" \
    --role="roles/datastore.user" >/dev/null 2>&1 || true

# Grant Cloud Storage Object Admin
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
    --member="serviceAccount:${DEFAULT_COMPUTE_SA}" \
    --role="roles/storage.objectAdmin" >/dev/null 2>&1 || true

# Grant Artifact Registry Writer
gcloud projects add-iam-policy-binding "$GCP_PROJECT" \
    --member="serviceAccount:${DEFAULT_COMPUTE_SA}" \
    --role="roles/artifactregistry.writer" >/dev/null 2>&1 || true

echo "✓ Granted Vertex AI, Firestore, Storage, and Artifact Registry IAM roles to ${DEFAULT_COMPUTE_SA}"

# 3. Optional Secret Manager Fallback for GEMINI_API_KEY (if present in .env)
HAS_SECRET="false"
if [ -z "${GEMINI_API_KEY:-}" ] && [ -f ".env" ]; then
    GEMINI_API_KEY=$(grep -E '^GEMINI_API_KEY=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
fi

if [ -n "${GEMINI_API_KEY:-}" ]; then
    echo ""
    echo "--> Syncing GEMINI_API_KEY to Secret Manager as secondary fallback..."
    if gcloud secrets describe GEMINI_API_KEY --project "$GCP_PROJECT" >/dev/null 2>&1; then
        printf "%s" "$GEMINI_API_KEY" | gcloud secrets versions add GEMINI_API_KEY --data-file=- --project "$GCP_PROJECT" >/dev/null
    else
        printf "%s" "$GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=- --replication-policy="automatic" --project "$GCP_PROJECT" >/dev/null
    fi
    gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
        --project "$GCP_PROJECT" \
        --member="serviceAccount:${DEFAULT_COMPUTE_SA}" \
        --role="roles/secretmanager.secretAccessor" >/dev/null 2>&1 || true
    HAS_SECRET="true"
    echo "✓ GEMINI_API_KEY synced to Secret Manager"
fi

# 4. Deploy to Google Cloud Run
echo ""
echo "=========================================================="
echo " Deploying $SERVICE_NAME to Google Cloud Run (Vertex AI mode)"
echo "=========================================================="

ENV_VARS="GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=${GCP_PROJECT},GOOGLE_CLOUD_LOCATION=global,GEMINI_LOCATION=global,OMNI_LOCATION=global,VEO_LOCATION=${REGION},DIRECTOR_MODEL=gemini-3.8-flash,VIDEO_MODEL=gemini-omni-1.1-flash-preview,MEDIA_BUCKET_NAME=${GCP_PROJECT}-media"

DEPLOY_ARGS=(
    --source .
    --project "$GCP_PROJECT"
    --region "$REGION"
    --platform managed
    --allow-unauthenticated
    --set-env-vars "$ENV_VARS"
    --min-instances 0
    --max-instances 3
    --memory 2Gi
    --cpu 2
    --timeout 300
)

if [ "$HAS_SECRET" = "true" ]; then
    DEPLOY_ARGS+=(--set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest")
fi

gcloud run deploy "$SERVICE_NAME" "${DEPLOY_ARGS[@]}"

echo ""
echo "=========================================================="
echo " Deployment completed successfully!"
echo " Service URL:"
gcloud run services describe "$SERVICE_NAME" --project "$GCP_PROJECT" --region "$REGION" --format="value(status.url)"
echo "=========================================================="
