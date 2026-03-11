import logging
import time

from bs4 import BeautifulSoup

from lncrawl.templates.browser.general import GeneralBrowserTemplate
from lncrawl.templates.novelfull import NovelFullTemplate

logger = logging.getLogger(__name__)

# Selectors to try for novel title, in priority order
_TITLE_SELECTORS = ["h3.title", "h1.title", ".novel-title", "h1"]


class Novel_Bin_Net(GeneralBrowserTemplate, NovelFullTemplate):
    has_mtl = False
    has_manga = False
    base_url = ["https://novel-bin.net/"]

    def initialize(self) -> None:
        self.init_executor(ratelimit=1)
        self.scraper.auto_refresh_on_403 = True
        self.scraper.max_403_retries = 3

    def visit_novel_page_in_browser(self) -> None:
        """Open novel URL and wait for content (Cloudflare challenge may delay it)."""
        self.visit(self.novel_url)
        for selector in _TITLE_SELECTORS:
            try:
                self.browser.wait(selector, timeout=10)
                return
            except Exception:
                continue
        logger.warning("No title element found yet, waiting for CF challenge...")
        time.sleep(5)

    def parse_title(self, soup: BeautifulSoup) -> str:
        """Try multiple title selectors, falling back to meta/title tags."""
        for selector in _TITLE_SELECTORS:
            tag = soup.select_one(selector)
            if tag and tag.text.strip():
                return tag.text.strip()
        meta = soup.select_one('meta[property="og:title"]')
        if meta and meta.get("content"):
            return str(meta["content"]).strip()
        title_tag = soup.select_one("title")
        if title_tag and title_tag.text.strip():
            title = title_tag.text.strip()
            if " - " in title:
                title = title.rsplit(" - ", 1)[0].strip()
            if title:
                return title
        raise AssertionError("Could not find novel title")
