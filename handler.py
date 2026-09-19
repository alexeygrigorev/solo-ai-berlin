"""API Gateway HTTP API v2 adapter for the WSGI application."""
from __future__ import annotations

import base64
from io import BytesIO

from server import application


def lambda_handler(event, context):
    if event.get('warmup'):
        return {'statusCode': 204, 'body': ''}
    method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    path = event.get('rawPath') or event.get('requestContext', {}).get('http', {}).get('path', '/')
    query = event.get('rawQueryString') or ''
    headers = {str(k).lower(): str(v) for k, v in (event.get('headers') or {}).items()}
    body = event.get('body') or b''
    if isinstance(body, str):
        body = base64.b64decode(body) if event.get('isBase64Encoded') else body.encode()
    environ = {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': query,
        'SERVER_NAME': headers.get('host', 'aiberlin.dtcdev.click'),
        'SERVER_PORT': '443',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https',
        'wsgi.input': BytesIO(body),
        'wsgi.errors': BytesIO(),
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': True,
        'CONTENT_TYPE': headers.get('content-type', ''),
        'CONTENT_LENGTH': str(len(body)),
        'REMOTE_ADDR': event.get('requestContext', {}).get('http', {}).get('sourceIp', ''),
        'HTTP_ORIGIN': headers.get('origin', ''),
        'HTTP_STRIPE_SIGNATURE': headers.get('stripe-signature', ''),
    }
    for name, value in headers.items():
        key = 'HTTP_' + name.upper().replace('-', '_')
        environ.setdefault(key, value)
    status_headers = []

    def start_response(status, response_headers, exc_info=None):
        status_headers.append((status, response_headers))

    chunks = application(environ, start_response)
    payload = b''.join(chunks)
    status, raw_headers = status_headers[0]
    code = int(status.split()[0])
    out_headers = {k: v for k, v in raw_headers}
    binary = not out_headers.get('Content-Type', '').startswith(('text/', 'application/json', 'application/xml', 'image/svg'))
    if binary:
        return {'statusCode': code, 'headers': out_headers, 'body': base64.b64encode(payload).decode(), 'isBase64Encoded': True}
    return {'statusCode': code, 'headers': out_headers, 'body': payload.decode('utf-8', 'replace'), 'isBase64Encoded': False}
