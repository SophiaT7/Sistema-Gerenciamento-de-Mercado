from pathlib import Path
from playwright.sync_api import sync_playwright

base = Path('report_images')
base.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1200})

    page.goto('http://127.0.0.1:8000/', timeout=30000)
    page.screenshot(path=str(base / 'login.png'), full_page=True)

    page.fill('#username', 'dono')
    page.fill('#password', 'dono123')
    page.locator("button[type='submit']").click()
    page.wait_for_timeout(4000)
    page.screenshot(path=str(base / 'dashboard.png'), full_page=True)

    page.goto('http://127.0.0.1:8000/produtos/', timeout=30000)
    page.screenshot(path=str(base / 'produtos.png'), full_page=True)

    page.goto('http://127.0.0.1:8000/entradas/', timeout=30000)
    page.screenshot(path=str(base / 'entradas.png'), full_page=True)

    page.goto('http://127.0.0.1:8000/pdv/', timeout=30000)
    page.screenshot(path=str(base / 'pdv.png'), full_page=True)

    browser.close()

print('screenshots-ok')
