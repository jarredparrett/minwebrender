import os
import re
from urllib.parse import urljoin, urlparse

import html2text
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

host = os.getenv("DOMAIN", "0.0.0.0:10000")

class BrowserService:
    def __init__(self, pool_size=5):
        self.pool_size = pool_size
        self.browsers = []
        self.playwright = None

    async def start(self):
        """Start multiple browser instances."""
        self.playwright = await async_playwright().start()
        for _ in range(self.pool_size):
            browser = await self.playwright.chromium.launch()
            self.browsers.append(browser)

    async def stop(self):
        """Close all browser instances."""
        for browser in self.browsers:
            await browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def render_page_and_extract_text(self, url):
        """Get an available browser, render the page, and extract text."""
        browser = self.browsers.pop(0)  # Get the first available browser
        page = await browser.new_page()
        await page.goto(url)
        content = await page.content()
        await page.close()
        self.browsers.append(browser)  # Return the browser to the pool

        return extract_text_content(content, url, host)

def extract_text_content(html_content, original_url, host_url):
    soup = BeautifulSoup(html_content, 'html.parser')

    for element in soup(['script', 'style', 'img']):
        element.decompose()

    for a in soup.find_all('a', href=True):
        original_href = a['href']
        parsed_href = urlparse(original_href)

        if parsed_href.scheme and parsed_href.netloc:
            new_href = f"{host_url}/{original_href.lstrip('/')}"
        else:
            full_href = urljoin(original_url, original_href)
            new_href = f"{host_url}/{full_href.lstrip('/')}"

        if not new_href.startswith(('http://', 'https://')):
            new_href = f"http://{new_href}"

        a['href'] = new_href

    markdown_content = html2text.HTML2Text()
    markdown_content.ignore_links = False
    markdown_content.body_width = 0
    markdown_text = markdown_content.handle(str(soup))

    markdown_text = re.sub(r'[ \t]+', ' ', markdown_text).strip()
    paragraphs = markdown_text.split('\n\n')
    formatted_markdown = '\n\n'.join(paragraph.strip() for paragraph in paragraphs)

    return formatted_markdown