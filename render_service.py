import os
import re
from urllib.parse import urljoin, urlparse

import html2text
from bs4 import BeautifulSoup

from asyncio import Semaphore, Queue, ensure_future
from playwright.async_api import async_playwright

host = os.getenv("DOMAIN", "0.0.0.0:10000")
max_pages_env = int(os.getenv("MAX_PAGES", 6))

class BrowserService:
    def __init__(self, max_pages=max_pages_env):
        self.browser = None
        self.playwright = None
        self.max_pages = max_pages
        self.page_semaphore = Semaphore(self.max_pages)
        self.queue = Queue()

    async def start(self):
        """Start the browser with limited concurrency."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

    async def stop(self):
        """Stop the browser and playwright."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def render_page_and_extract_text(self, url):
        """Enqueue the request and wait for it to be processed."""
        future = ensure_future(self.queue_page_request(url))
        return await future

    async def queue_page_request(self, url):
        """Queue a request and process it when a page is available."""
        async with self.page_semaphore:
            return await self.process_page(url)

    async def process_page(self, url):
        """Process a single page and return the content."""
        page = await self.browser.new_page()
        try:
            await page.goto(url, timeout=60000)  # 60 seconds timeout
            content = await page.content()
            return extract_text_content(content, url, host)
        finally:
            await page.close()


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