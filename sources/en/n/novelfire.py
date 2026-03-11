import logging
from typing import Generator, Optional, Union

from bs4 import BeautifulSoup, Tag

from lncrawl.models import Chapter, SearchResult, Volume
from lncrawl.templates.soup.general import GeneralSoupTemplate
from lncrawl.templates.soup.searchable import SearchableSoupTemplate

logger = logging.getLogger(__name__)


class NovelFireCrawler(SearchableSoupTemplate, GeneralSoupTemplate):
    base_url = [
        "https://novelfire.net/",
    ]
    has_mtl = False
    has_manga = False

    def initialize(self) -> None:
        self.init_executor(ratelimit=1)

    def select_search_items(self, query: str) -> Generator[Tag, None, None]:
        soup = self.get_soup(f"{self.home_url}search?keyword={query}")
        yield from soup.select(".novel-list .novel-item a.novel-title")

    def parse_search_item(self, tag: Tag) -> SearchResult:
        return SearchResult(
            title=tag.get_text(strip=True),
            url=self.absolute_url(tag["href"]),
        )

    def parse_title(self, soup: BeautifulSoup) -> str:
        tag = soup.select_one("h1.novel-title")
        assert tag
        return tag.get_text(strip=True)

    def parse_cover(self, soup: BeautifulSoup) -> str:
        tag = soup.select_one("figure.cover img")
        if tag:
            return self.absolute_url(tag["src"])
        return ""

    def parse_authors(self, soup: BeautifulSoup) -> Generator[str, None, None]:
        tag = soup.select_one('span[itemprop="author"]')
        if tag:
            yield tag.get_text(strip=True)

    def parse_chapter_list(
        self, soup: BeautifulSoup
    ) -> Generator[Union[Chapter, Volume], None, None]:
        chapters_url = self.novel_url.rstrip("/") + "/chapters"
        page = 1

        while True:
            url = chapters_url if page == 1 else f"{chapters_url}?page={page}"
            list_soup = self.get_soup(url)

            items = list_soup.select("ul.chapter-list li a")
            if not items:
                break

            for a in items:
                chap_id = len(self.chapters) + 1
                title_tag = a.select_one("strong.chapter-title")
                title = title_tag.get_text(strip=True) if title_tag else a.get("title", f"Chapter {chap_id}")
                yield Chapter(
                    id=chap_id,
                    title=title,
                    url=self.absolute_url(a["href"]),
                )

            next_link = list_soup.select_one("a.page-link[rel='next']")
            if next_link:
                page += 1
            else:
                break

    def select_chapter_body(self, soup: BeautifulSoup) -> Optional[Tag]:
        return soup.select_one("div#content")
