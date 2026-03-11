import logging

from lncrawl.templates.browser.general import GeneralBrowserTemplate
from lncrawl.templates.novelfull import NovelFullTemplate

logger = logging.getLogger(__name__)


class Novelbin_Net(GeneralBrowserTemplate, NovelFullTemplate):
    has_mtl = False
    has_manga = False
    base_url = ["https://novelbin.net/"]

    def initialize(self) -> None:
        self.init_executor(ratelimit=0.99)
        self.scraper.auto_refresh_on_403 = True
        self.scraper.max_403_retries = 3
