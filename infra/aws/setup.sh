#!/usr/bin/env bash
# Phase 0 AWS setup: auction-lake bucket + public-access block + $10 budget alarm.
# Prereqs: aws CLI configured with an admin profile; then create the
# least-privilege user with iam_policy.json and use THAT for daily work.
set -euo pipefail

BUCKET="${TRIBUTARY_S3_BUCKET:?Set TRIBUTARY_S3_BUCKET (e.g. tributary-auction-lake-jb42)}"
REGION="${AWS_REGION:-us-east-1}"
ALERT_EMAIL="${ALERT_EMAIL:?Set ALERT_EMAIL for budget notifications}"

echo ">> Creating bucket s3://${BUCKET} in ${REGION}"
if [ "$REGION" = "us-east-1" ]; then
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION"
else
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION"
fi

echo ">> Blocking all public access"
aws s3api put-public-access-block --bucket "$BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

echo ">> Creating \$10/month budget with alerts at 50%/80%/100%"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
sed "s/ALERT_EMAIL/${ALERT_EMAIL}/" "$(dirname "$0")/budget-notifications.json" > /tmp/tributary-notifications.json
aws budgets create-budget \
  --account-id "$ACCOUNT_ID" \
  --budget file://"$(dirname "$0")"/budget.json \
  --notifications-with-subscribers file:///tmp/tributary-notifications.json

echo ">> Done. Now create the least-privilege IAM user:"
echo "   aws iam create-user --user-name tributary"
echo "   aws iam put-user-policy --user-name tributary --policy-name tributary-s3 \\"
echo "     --policy-document file://$(dirname "$0")/iam_policy.json   # edit bucket name first"
echo "   aws iam create-access-key --user-name tributary   # -> aws configure --profile tributary"
