# Solo AI Berlin

**Build your business with AI. Not alone.**

A small, application-based peer group in Berlin for solopreneurs and indie hackers using AI to build independent businesses. Public site: [https://aiberlin.dtcdev.click](https://aiberlin.dtcdev.click).

| Pilot | 10 and 24 November 2026, 18:30-21:00 CET |
| --- | --- |
| Place | Mitte / Prenzlauer Berg (venue confirmed by 3 November) |
| Size | 10-12 paying participants, plus the host |
| Price | €59 + 19% VAT (€70.21 at checkout), one-time, via Stripe |
| Deadline | Applications and payment by 1 November 2026, 23:59 CET |

Payment is an advance. It does not guarantee a place. Full refund if declined, the group is full, the threshold is missed, or the organiser cancels.

## Local preview

Python 3.10+. No extra packages for the server.

```bash
python server.py
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080). In preview mode the form validates but does not send or charge.

```bash
python qa/test_backend.py
```

## Stripe-ready checkout

The live site already exposes:

- `POST /api/applications` — saves the form, returns a Stripe Payment Link URL with `client_reference_id`
- `POST /api/stripe-webhook` — verifies Stripe signatures for `checkout.session.completed`, `checkout.session.async_payment_succeeded`, and `checkout.session.async_payment_failed`

Until a Payment Link is configured, the public pages stay up and checkout returns a clear “not connected yet” error.

1. In Stripe, create a **Payment Link** for **EUR 59.00 net**, quantity 1, no subscription. Turn on tax so **19% German VAT is added on top** (€70.21 charged). Do not include VAT in the €59.
2. Success URL: `https://aiberlin.dtcdev.click/?checkout=returned`
3. Webhook endpoint: `https://aiberlin.dtcdev.click/api/stripe-webhook` for the three events above.
4. Store these as SSM SecureString parameters in `eu-west-1`, then redeploy:

```
/solo-ai-berlin/stripe-payment-link        https://buy.stripe.com/...
/solo-ai-berlin/stripe-payment-link-id     plink_...
/solo-ai-berlin/stripe-webhook-secret      whsec_...
```

```bash
./scripts/deploy.sh
```

Use a test Payment Link and `STRIPE_LIVEMODE=false` first. Switch to live keys only after a full test payment and refund.

Never put `sk_` keys in this repository or in `index.html`. The server only needs the public Payment Link, its `plink_` id, and the webhook signing secret.

## Deploy

The site runs on AWS Lambda + API Gateway HTTP API + DynamoDB + ACM + Route 53, same pattern as other `*.dtcdev.click` apps.

```bash
./scripts/deploy.sh
```

Operator: DataTalks.Club, Alexey Grigorev, Berlin. Legal pages: [Impressum](https://aiberlin.dtcdev.click/legal/impressum), [privacy](https://aiberlin.dtcdev.click/legal/privacy), [pilot terms](https://aiberlin.dtcdev.click/legal/terms).

## Planning notes

Research and messaging that led to this pilot live in [docs/](docs/). They are planning archives, not the live offer.
