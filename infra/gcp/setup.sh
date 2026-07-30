#!/usr/bin/env bash
# Phase 0 GCP setup: BigQuery marketing dataset + budget alert.
# Prereqs: gcloud CLI, `gcloud auth login`, and a project created in the console.
set -euo pipefail

PROJECT="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
DATASET="${BQ_MARKETING_DATASET:-clx_marketing}"
LOCATION="${BQ_LOCATION:-US}"

gcloud config set project "$PROJECT"
gcloud services enable bigquery.googleapis.com

echo ">> Creating BigQuery dataset ${DATASET}"
bq --location="$LOCATION" mk --dataset --description "CLX marketing silo (ESP exports)" "${PROJECT}:${DATASET}"

echo ">> Setting up application-default credentials for local clients"
gcloud auth application-default login

cat <<'EOF'
>> Budget alert: the gcloud billing budgets API needs the billing account ID:
     gcloud billing accounts list
     gcloud billing budgets create --billing-account=BILLING_ACCOUNT_ID \
       --display-name="tributary" --budget-amount=10USD \
       --threshold-rule=percent=0.5 --threshold-rule=percent=0.8 --threshold-rule=percent=1.0
   (Or set it in the console: Billing -> Budgets & alerts. Screenshot it for the write-up.)
EOF
