# -*- coding: utf-8 -*-
import logging

from lncrawl.templates.browser.general import GeneralBrowserTemplate
from lncrawl.templates.novelfull import NovelFullTemplate

logger = logging.getLogger(__name__)


class NovelbinCrawler(GeneralBrowserTemplate, NovelFullTemplate):
    base_url = ["https://novelbin.com/"]

    def initialize(self) -> None:
        self.init_executor(ratelimit=0.99)
        # Enable 403 auto-recovery for this source
        self.scraper.auto_refresh_on_403 = True
        self.scraper.max_403_retries = 3
