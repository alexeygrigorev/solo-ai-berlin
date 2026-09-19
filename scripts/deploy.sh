#!/usr/bin/env bash
# Package the site and deploy via CloudFormation. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-eu-west-1}"
STACK="${STACK:-solo-ai-berlin}"
DOMAIN="${DOMAIN:-aiberlin.dtcdev.click}"
ZONE="${ZONE:-Z05963572WVWFHDQZH5NE}"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="solo-ai-berlin-deploy-${ACCOUNT}-${REGION}"
KEY="lambda/build-$(date +%s).zip"

echo "==> packaging"
rm -rf build/pkg
mkdir -p build/pkg/legal build/pkg/assets
cp handler.py server.py store.py manage.py index.html build/pkg/
cp legal/*.html build/pkg/legal/
cp assets/* build/pkg/assets/
rm -f build/lambda.zip
python3 -c "import shutil; shutil.make_archive('build/lambda','zip','build/pkg')"
echo "    package: $(du -h build/lambda.zip | cut -f1)"

echo "==> ensuring code bucket ${BUCKET}"
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION" >/dev/null
fi
aws s3 cp build/lambda.zip "s3://${BUCKET}/${KEY}" >/dev/null

read_ssm() {
  local name="$1"
  aws ssm get-parameter --region "$REGION" --name "$name" --with-decryption \
    --query 'Parameter.Value' --output text 2>/dev/null || true
}

PAYMENT_LINK="${STRIPE_PAYMENT_LINK:-$(read_ssm /solo-ai-berlin/stripe-payment-link)}"
PAYMENT_LINK_ID="${STRIPE_PAYMENT_LINK_ID:-$(read_ssm /solo-ai-berlin/stripe-payment-link-id)}"
WEBHOOK_SECRET="${STRIPE_WEBHOOK_SECRET:-$(read_ssm /solo-ai-berlin/stripe-webhook-secret)}"
CONTACT="${CONTACT_EMAIL:-$(read_ssm /solo-ai-berlin/contact-email)}"
CONTACT="${CONTACT:-alexey@datatalks.club}"
LIVE_MODE="${STRIPE_LIVEMODE:-false}"

echo "==> deploying CloudFormation stack ${STACK} (region ${REGION})"
aws cloudformation deploy --region "$REGION" --stack-name "$STACK" \
  --template-file infra/cloudformation.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    CodeBucket="$BUCKET" CodeKey="$KEY" \
    DomainName="$DOMAIN" HostedZoneId="$ZONE" \
    ContactEmail="$CONTACT" \
    AppMode=live LegalReady=true \
    StripeLivemode="$LIVE_MODE" \
    StripePaymentLink="${PAYMENT_LINK:-}" \
    StripePaymentLinkId="${PAYMENT_LINK_ID:-}" \
    StripeWebhookSecret="${WEBHOOK_SECRET:-}"

echo "==> outputs"
aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs" --output table
echo
echo "Site: https://${DOMAIN}"
echo "Stripe webhook: https://${DOMAIN}/api/stripe-webhook"
echo "To connect checkout, put a Payment Link, plink_ id and whsec_ in"
echo "SSM /solo-ai-berlin/stripe-payment-link, stripe-payment-link-id,"
echo "stripe-webhook-secret (SecureString) and re-run this script."
