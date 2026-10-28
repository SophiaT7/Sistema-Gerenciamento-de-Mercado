from playwright.sync_api import sync_playwright

import re
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1200})
    page.goto('http://127.0.0.1:8000/login/', timeout=30000)
    page.fill('#username', 'dono')
    page.fill('#password', 'dono123')
    page.locator("button[type='submit']").click()
    page.wait_for_timeout(5000)
    body_text = page.locator('body').inner_text()
    print('URL2', page.url)
    print('HAS_ERROR', 'Credenciais inválidas' in body_text)
    print('BODY_AFTER_LOGIN_START')
    print(re.sub(r'[^\x00-\x7F]+', '', body_text)[:1500])
    print('BODY_AFTER_LOGIN_END')
    browser.close()
