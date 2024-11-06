from __future__ import annotations

from typing import TYPE_CHECKING

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import NoExtensionFailure, ScrapeItemMaxChildrenReached
from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import FILE_HOST_ALBUM, ScrapeItem
from cyberdrop_dl.utils.utilities import error_handling_wrapper, get_filename_and_ext, log

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

    from cyberdrop_dl.managers.manager import Manager


class XBunkrCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "xbunkr", "XBunkr")
        self.request_limiter = AsyncLimiter(10, 1)

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)

        if "media" in scrape_item.url.host:
            filename, ext = await get_filename_and_ext(scrape_item.url.name)
            await self.handle_file(scrape_item.url, scrape_item, filename, ext)
        else:
            await self.album(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a profile"""
        async with self.request_limiter:
            soup: BeautifulSoup = await self.client.get_BS4(self.domain, scrape_item.url, origin=scrape_item)

        scrape_item.album_id = scrape_item.url.parts[2]
        scrape_item.part_of_album = True

        scrape_item.type = FILE_HOST_ALBUM
        scrape_item.children = scrape_item.children_limit = 0

        try:
            scrape_item.children_limit = self.manager.config_manager.settings_data["Download_Options"][
                "maximum_number_of_children"
            ][scrape_item.type]
        except (IndexError, TypeError):
            pass

        title = await self.create_title(soup.select_one("h1[id=title]").text, scrape_item.album_id, None)

        links = soup.select("a[class=image]")
        for link in links:
            link = URL(link.get("href"))
            try:
                filename, ext = await get_filename_and_ext(link.name)
            except NoExtensionFailure:
                await log(f"Couldn't get extension for {str(link)}", 30)
                continue
            new_scrape_item = await self.create_scrape_item(scrape_item, link, title, True, add_parent=scrape_item.url)
            await self.handle_file(link, new_scrape_item, filename, ext)
            scrape_item.children += 1
            if scrape_item.children_limit:
                if scrape_item.children >= scrape_item.children_limit:
                    raise ScrapeItemMaxChildrenReached(origin=scrape_item)
