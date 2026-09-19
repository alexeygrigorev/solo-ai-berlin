from pathlib import Path
import json
import threading
from wsgiref.simple_server import make_server
from playwright.sync_api import sync_playwright
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

root = Path(__file__).resolve().parents[1]
httpd = make_server('127.0.0.1', 0, server.application)
port = httpd.server_port
thread = threading.Thread(target=httpd.serve_forever, daemon=True)
thread.start()
base = f'http://127.0.0.1:{port}'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    errors = []
    page = browser.new_page(viewport={'width': 1440, 'height': 1050}, device_scale_factor=1)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(base, wait_until='networkidle')
    page.screenshot(path=str(root / 'qa/desktop-full.png'), full_page=True)
    page.screenshot(path=str(root / 'qa/desktop-hero.png'))
    assert page.locator('h1').count() == 1
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    page.locator('[data-next]').first.click()
    assert page.locator('[data-step="0"]').is_visible()
    vals = {'name': 'Test Founder', 'email': 'founder@example.com', 'location': 'Berlin Mitte', 'profile': 'https://example.com', 'project': 'I am building a small service for independent founders to automate customer support with AI.'}
    for name, value in vals.items():
        page.locator(f'[name="{name}"]').fill(value)
    page.locator('[name="stage"]').select_option('building')
    page.locator('[data-next]').first.click()
    assert page.locator('[data-step="1"]').is_visible()
    for name in ['recent', 'aiWork', 'contribution', 'challenge']:
        page.locator(f'[name="{name}"]').fill('I tested a concrete AI workflow in my current business and would share results, tradeoffs and useful failures with the group.')
    page.locator('[data-step="1"] [data-next]').click()
    assert page.locator('[data-step="2"]').is_visible()
    for name in ['attendance', 'participation', 'paymentTerms', 'privacy']:
        page.locator(f'[name="{name}"]').check()
    page.locator('#submit-button').click()
    assert page.locator('#preview-dialog').is_visible()
    assert 'Nothing has been submitted' in page.locator('#dialog-body').inner_text()
    page.locator('#preview-dialog [data-close]').last.click()
    page.locator('[data-step="2"] [data-back]').click()
    assert 'concrete AI workflow' in page.locator('[name="aiWork"]').input_value()
    page.locator('#faq details').first.locator('summary').click()
    assert page.locator('#faq details').first.get_attribute('open') is not None
    footer = page.locator('footer')
    assert footer.get_by_role('link', name='Impressum').get_attribute('href') == '/legal/impressum'
    legal = browser.new_page(viewport={'width': 1440, 'height': 900})
    legal.goto(f'{base}/legal/impressum', wait_until='networkidle')
    assert legal.locator('h1').inner_text() == 'Impressum'
    assert 'Schonensche Straße 13' in legal.locator('main').inner_text()
    legal.screenshot(path=str(root / 'qa/impressum-desktop.png'), full_page=True)
    legal.close()
    for w in [360, 390, 768, 1024]:
        mobile = browser.new_page(viewport={'width': w, 'height': 844}, device_scale_factor=1)
        mobile.on('pageerror', lambda e: errors.append(str(e)))
        mobile.goto(base, wait_until='networkidle')
        assert not mobile.evaluate('document.documentElement.scrollWidth > innerWidth'), f'Overflow at {w}'
        if w == 390:
            mobile.screenshot(path=str(root / 'qa/mobile-full.png'), full_page=True)
            mobile.screenshot(path=str(root / 'qa/mobile-hero.png'))
            mobile.goto(f'{base}/legal/impressum', wait_until='networkidle')
            assert not mobile.evaluate('document.documentElement.scrollWidth > innerWidth')
            mobile.screenshot(path=str(root / 'qa/impressum-mobile.png'), full_page=True)
        mobile.close()
    print(json.dumps({'browser': 'Chromium', 'viewports': [360, 390, 768, 1024, 1440], 'console_errors': errors, 'checks': ['required fields', 'three-step navigation', 'preview does not submit', 'back preserves answers', 'FAQ accordion', 'no horizontal overflow', 'impressum']}, indent=2))
    assert not errors
    browser.close()
httpd.shutdown()
