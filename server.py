"""Optional, dependency-free WSGI backend for the founding pilot.

Local preview: python server.py
Production: use a maintained WSGI server behind HTTPS, with persistent storage.
Never expose the development server or private-data directory publicly.
No card details are collected. This program cannot charge or refund anyone.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import store

ROOT = Path(__file__).resolve().parent
os.umask(0o077)
# Minimal .env support. Values are literal, without shell expansion.
if (ROOT / '.env').exists():
    for raw in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            if re.fullmatch(r'[A-Z][A-Z0-9_]*', key.strip()):
                os.environ.setdefault(key.strip(), value.strip().strip('\"\''))

MODE = os.getenv('APP_MODE', 'preview')
ORIGIN = os.getenv('PUBLIC_ORIGIN', 'http://localhost:8080').rstrip('/')
CONTACT = os.getenv('CONTACT_EMAIL', '')
PAYMENT_LINK = os.getenv('STRIPE_PAYMENT_LINK', '')
PAYMENT_LINK_ID = os.getenv('STRIPE_PAYMENT_LINK_ID', '')
WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
LIVE_PAYMENTS = os.getenv('STRIPE_LIVEMODE', 'false').lower() == 'true'
CLOSES = datetime.fromisoformat('2026-11-01T23:59:00+01:00').timestamp()
TERMS_VERSION = 'founding-pilot-2026-09-19-v2'
PRICE_NET_CENTS = 5900
PRICE_GROSS_CENTS = 7021  # €59.00 net + 19% German VAT = €70.21
STATIC_TYPES = {
    '.css': 'text/css; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.txt': 'text/plain; charset=utf-8',
    '.xml': 'application/xml; charset=utf-8',
    '.ico': 'image/x-icon',
    '.woff2': 'font/woff2',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
}
MAX_BODY = 48_000
TEXT_RULES = {
    'name': (1, 120), 'email': (3, 254), 'location': (1, 180),
    'project': (30, 2000), 'recent': (25, 2000), 'aiWork': (25, 2000),
    'contribution': (20, 1500), 'challenge': (20, 1500),
    'profile': (0, 500), 'notes': (0, 1500),
}
CONSENTS = ('attendance', 'participation', 'paymentTerms', 'privacy')

class ClientError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def check_live_configuration() -> None:
    if MODE not in {'preview', 'live'}:
        raise RuntimeError('APP_MODE must be preview or live.')
    if MODE != 'live':
        return
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', CONTACT):
        raise RuntimeError('Set the organiser contact email.')
    if PAYMENT_LINK or PAYMENT_LINK_ID or WEBHOOK_SECRET:
        parsed = urlsplit(PAYMENT_LINK)
        if parsed.scheme != 'https' or parsed.netloc != 'buy.stripe.com' or parsed.path == '/':
            raise RuntimeError('Set a real Stripe-hosted Payment Link.')
        if not PAYMENT_LINK_ID.startswith('plink_') or not WEBHOOK_SECRET.startswith('whsec_'):
            raise RuntimeError('Payment Link ID and endpoint signing secret are required.')
    if LIVE_PAYMENTS and (not ORIGIN.startswith('https://') or parsed.path.startswith('/test_')):
        raise RuntimeError('Real payments require HTTPS and a live Payment Link.')
    if os.getenv('LEGAL_READY') != 'true':
        raise RuntimeError('Complete the legal pages and set LEGAL_READY=true before opening applications.')
    for name in ('privacy', 'terms', 'impressum'):
        content = (ROOT / 'legal' / f'{name}.html').read_text(encoding='utf-8')
        if '[[REPLACE' in content or 'DRAFT — DO NOT PUBLISH' in content:
            raise RuntimeError(f'Finish legal/{name}.html before opening applications.')


def stripe_configured() -> bool:
    parsed = urlsplit(PAYMENT_LINK)
    return (
        parsed.scheme == 'https'
        and parsed.netloc == 'buy.stripe.com'
        and PAYMENT_LINK_ID.startswith('plink_')
        and WEBHOOK_SECRET.startswith('whsec_')
    )


def connect() -> sqlite3.Connection:
    return store.connect()


def initialise_database() -> None:
    store.initialise_database()


def build_checkout_url(application_id: str) -> str:
    parts = urlsplit(PAYMENT_LINK)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query['client_reference_id'] = application_id
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))


def read_body(environ: dict, maximum: int = MAX_BODY) -> bytes:
    try:
        size = int(environ.get('CONTENT_LENGTH') or 0)
    except ValueError:
        raise ClientError(400, 'Invalid request length.')
    if not 0 < size <= maximum:
        raise ClientError(413, 'The request is empty or too large.')
    raw = environ['wsgi.input'].read(size)
    if len(raw) != size:
        raise ClientError(400, 'Incomplete request.')
    return raw


def enforce_rate_limit(environ: dict) -> None:
    # REMOTE_ADDR is deliberately not taken from an untrusted forwarded header.
    # Configure trusted proxy handling and an edge rate limit when deploying.
    now = int(time.time())
    address = str(environ.get('REMOTE_ADDR', 'unknown'))
    secret = WEBHOOK_SECRET or ORIGIN or 'preview-rate-limit'
    key = hmac.new(secret.encode(), address.encode(), hashlib.sha256).hexdigest()
    if store.rate_limit(key, now):
        raise ClientError(429, 'Too many attempts. Please wait a few minutes before trying again.')


def save_application(environ: dict) -> dict:
    if MODE != 'live':
        raise ClientError(503, 'This is a preview. Applications and payments are not open.')
    if not stripe_configured():
        raise ClientError(503, 'Applications are ready, but Stripe checkout is not connected yet. Please contact the organiser.')
    if time.time() > CLOSES:
        raise ClientError(410, 'Applications for this pilot are closed.')
    if environ.get('HTTP_ORIGIN') != ORIGIN:
        raise ClientError(403, 'Please submit the application from the official website.')
    if environ.get('CONTENT_TYPE', '').split(';')[0].strip() != 'application/json':
        raise ClientError(415, 'Expected a JSON request.')
    enforce_rate_limit(environ)
    try:
        incoming = json.loads(read_body(environ))
    except (ValueError, UnicodeError):
        raise ClientError(400, 'The application could not be read.')
    if not isinstance(incoming, dict) or incoming.get('websiteConfirm'):
        raise ClientError(400, 'The application could not be accepted.')
    clean = {}
    for key, (minimum, maximum) in TEXT_RULES.items():
        value = incoming.get(key, '')
        if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
            raise ClientError(422, f'Please check the answer for {key}.')
        clean[key] = value.strip()
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', clean['email']):
        raise ClientError(422, 'Please use a valid email address.')
    if clean['profile'] and urlsplit(clean['profile']).scheme not in ('http', 'https'):
        raise ClientError(422, 'Please use a full http or https link to your work.')
    stage = incoming.get('stage')
    if stage not in {'validating', 'building', 'running', 'other'}:
        raise ClientError(422, 'Please choose your project stage.')
    clean['stage'] = stage
    for key in CONSENTS:
        if incoming.get(key) not in (True, 'on'):
            raise ClientError(422, 'Please confirm the dates, participation and payment conditions.')
        clean[key] = True
    key = incoming.get('submissionKey', '')
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{20,100}', key):
        raise ClientError(422, 'The application reference is missing. Please reload the page.')
    payload = json.dumps(clean, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    old = store.get_application_by_submission(key)
    if old:
        if not hmac.compare_digest(old['payload_hash'], digest):
            raise ClientError(409, 'This application was already saved with different answers. Please contact the organiser to update it before paying.')
        application_id = old['id']
    else:
        application_id = 'app_' + uuid.uuid4().hex
        store.insert_application(application_id, key, digest, int(time.time()), payload, TERMS_VERSION)
    return {'applicationId': application_id, 'checkoutUrl': build_checkout_url(application_id)}


def verify_stripe_signature(raw: bytes, header: str, secret: str, now: int | None = None) -> None:
    """Stripe's documented manual HMAC-SHA256 verification; 5-minute tolerance."""
    pieces = [part.strip().split('=', 1) for part in header.split(',') if '=' in part]
    timestamps = [value for name, value in pieces if name == 't']
    signatures = [value for name, value in pieces if name == 'v1' and re.fullmatch(r'[a-fA-F0-9]{64}', value)]
    if len(timestamps) != 1 or not signatures or not timestamps[0].isdigit():
        raise ClientError(400, 'Invalid Stripe signature.')
    timestamp = timestamps[0]
    if abs((int(time.time()) if now is None else now) - int(timestamp)) > 300:
        raise ClientError(400, 'Expired Stripe signature.')
    expected = hmac.new(secret.encode(), timestamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, signature.lower()) for signature in signatures):
        raise ClientError(400, 'Invalid Stripe signature.')


def handle_webhook(environ: dict) -> dict:
    if not WEBHOOK_SECRET:
        raise ClientError(503, 'Webhook is not configured.')
    raw = read_body(environ, 1_000_000)
    verify_stripe_signature(raw, environ.get('HTTP_STRIPE_SIGNATURE', ''), WEBHOOK_SECRET)
    try:
        event = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ClientError(400, 'Invalid event body.')
    if not isinstance(event, dict) or not str(event.get('id', '')).startswith('evt_'):
        raise ClientError(400, 'Invalid event.')
    if event.get('livemode') is not LIVE_PAYMENTS:
        raise ClientError(400, 'Unexpected Stripe environment.')
    kind = event.get('type', '')
    if kind not in {'checkout.session.completed', 'checkout.session.async_payment_succeeded', 'checkout.session.async_payment_failed'}:
        return {'received': True, 'ignored': True}
    session = event.get('data', {}).get('object', {})
    session_id = session.get('id', '')
    if not isinstance(session_id, str) or not session_id.startswith('cs_'):
        raise ClientError(400, 'Invalid checkout session.')
    now = int(time.time())
    if store.event_seen(event['id']):
        return {'received': True, 'duplicate': True}
    if session.get('payment_link') != PAYMENT_LINK_ID:
        store.mark_event(event['id'], kind, now)
        return {'received': True, 'ignored': True}
    reference = session.get('client_reference_id')
    row = store.get_application(reference) if isinstance(reference, str) else None
    application_id = row['id'] if row else None
    amount, currency = session.get('amount_total'), session.get('currency')
    subtotal = session.get('amount_subtotal')
    net_ok = subtotal == PRICE_NET_CENTS or (subtotal is None and amount == PRICE_GROSS_CENTS)
    valid_price = currency == 'eur' and net_ok and amount == PRICE_GROSS_CENTS
    paid = session.get('payment_status') == 'paid'
    status = 'paid' if paid and valid_price and application_id else 'needs_review'
    if not paid and application_id and valid_price:
        status = 'failed' if kind.endswith('async_payment_failed') else 'pending'
    flags = []
    if not application_id:
        flags.append('unmatched_application')
    if not valid_price:
        flags.append('unexpected_amount_or_currency')
    event_created = event.get('created')
    if isinstance(event_created, (int, float)) and event_created > CLOSES:
        flags.append('payment_after_application_deadline')
    if application_id and store.has_other_paid(application_id, session_id):
        flags.append('possible_duplicate_payment')
    previous = store.previous_payment_status(session_id)
    if previous == 'paid':
        status = 'paid'
    intent = session.get('payment_intent')
    if isinstance(intent, dict):
        intent = intent.get('id')
    store.upsert_payment(session_id, application_id, intent, status, amount, currency, now, ','.join(flags))
    store.mark_event(event['id'], kind, now)
    return {'received': True}


def respond(start_response, status: int, payload: bytes, content_type: str = 'application/json; charset=utf-8'):
    headers = [('Content-Type', content_type), ('Content-Length', str(len(payload))),
               ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'),
               ('Referrer-Policy', 'no-referrer'), ('X-Frame-Options', 'DENY'),
               ('Permissions-Policy', 'camera=(), microphone=(), geolocation=()'),
               ('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")]
    if ORIGIN.startswith('https://'):
        headers.append(('Strict-Transport-Security', 'max-age=31536000'))
    start_response(f'{status} {HTTPStatus(status).phrase}', headers)
    return [payload]


def application(environ, start_response):
    try:
        method, path = environ.get('REQUEST_METHOD', 'GET'), environ.get('PATH_INFO', '/')
        if method == 'GET' and path in ('/', '/index.html'):
            html = (ROOT / 'index.html').read_text(encoding='utf-8')
            if MODE == 'live':
                config = dict(mode='live', applicationEndpoint='/api/applications',
                              privacyUrl='/legal/privacy', termsUrl='/legal/terms',
                              imprintUrl='/legal/impressum', contactEmail=CONTACT,
                              applicationsClose='2026-11-01T23:59:00+01:00')
                encoded = json.dumps(config).replace('<', '\\u003c')
                html = re.sub(r'(<script id="site-config" type="application/json">).*?(</script>)',
                              lambda m: m[1] + encoded + m[2], html, count=1, flags=re.S)
                if stripe_configured() and not LIVE_PAYMENTS:
                    html = html.replace("document.getElementById('preview-bar').hidden=true;", "document.getElementById('preview-bar').textContent='TEST CHECKOUT — not a live application. Use test details only.';")
                    html = html.replace("document.getElementById('robots-meta').content='index,follow';", "document.getElementById('robots-meta').content='noindex,nofollow';")
            return respond(start_response, 200, html.encode(), 'text/html; charset=utf-8')
        if method == 'GET' and path in {'/legal/imprint', '/legal/imprint.html'}:
            start_response('302 Found', [('Location', '/legal/impressum'), ('Cache-Control', 'no-store')])
            return [b'']
        if method == 'GET' and path in {'/legal/privacy', '/legal/terms', '/legal/impressum', '/legal/privacy.html', '/legal/terms.html', '/legal/impressum.html'}:
            name = path.rsplit('/', 1)[1].removesuffix('.html')
            content = (ROOT / 'legal' / f'{name}.html').read_bytes()
            return respond(start_response, 200, content, 'text/html; charset=utf-8')
        if method == 'GET' and path.startswith('/assets/'):
            relative = path[len('/assets/'):]
            if '..' in Path(relative).parts or relative.startswith('/') or not relative:
                raise ClientError(404, 'Not found.')
            target = (ROOT / 'assets' / relative).resolve()
            assets_root = (ROOT / 'assets').resolve()
            if not str(target).startswith(str(assets_root) + '/') or not target.is_file():
                raise ClientError(404, 'Not found.')
            return respond(start_response, 200, target.read_bytes(), STATIC_TYPES.get(target.suffix, 'application/octet-stream'))
        if method == 'GET' and path in {'/robots.txt', '/sitemap.xml'}:
            target = ROOT / 'assets' / path.lstrip('/')
            return respond(start_response, 200, target.read_bytes(), STATIC_TYPES[Path(path).suffix])
        if method == 'GET' and path == '/health':
            return respond(start_response, 200, json.dumps({'ok': True, 'stripe': stripe_configured()}).encode())
        if method == 'POST' and path == '/api/applications':
            result = save_application(environ)
            return respond(start_response, 200, json.dumps(result).encode())
        if method == 'POST' and path == '/api/stripe-webhook':
            result = handle_webhook(environ)
            return respond(start_response, 200, json.dumps(result).encode())
        raise ClientError(404, 'Not found.')
    except ClientError as exc:
        return respond(start_response, exc.status, json.dumps({'error': exc.message}).encode())
    except Exception as exc:
        # No form values, email addresses, secrets or request bodies in logs.
        logging.error('Request failed (%s)', type(exc).__name__)
        return respond(start_response, 500, b'{"error":"A server error occurred. Your payment has not been started; please retry or contact the organiser."}')

check_live_configuration()
initialise_database()

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    on_lambda = bool(os.getenv('AWS_LAMBDA_FUNCTION_NAME'))
    host = '0.0.0.0' if on_lambda else '127.0.0.1'
    port = int(os.getenv('AWS_LWA_PORT') or os.getenv('PORT') or 8080)
    if LIVE_PAYMENTS and not on_lambda:
        raise SystemExit('Do not use the development server for real payments. Use a production WSGI server behind HTTPS.')
    if not on_lambda:
        print(f'Local preview only: http://127.0.0.1:{port} — not a public production server.')
    with make_server(host, port, application) as httpd:
        httpd.serve_forever()
