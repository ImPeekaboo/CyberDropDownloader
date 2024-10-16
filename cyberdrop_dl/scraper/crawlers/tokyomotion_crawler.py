from __future__ import annotations

from typing import TYPE_CHECKING, AsyncGenerator

from aiolimiter import AsyncLimiter
from yarl import URL

from cyberdrop_dl.clients.errors import ScrapeFailure
from cyberdrop_dl.scraper.crawler import Crawler
from cyberdrop_dl.utils.dataclasses.url_objects import ScrapeItem
from cyberdrop_dl.utils.utilities import log, get_filename_and_ext, error_handling_wrapper

if TYPE_CHECKING:
    from cyberdrop_dl.managers.manager import Manager
    from bs4 import BeautifulSoup

class TokioMotionCrawler(Crawler):
    def __init__(self, manager: Manager):
        super().__init__(manager, "tokyomotion", "Tokyomotion")
        self.primary_base_domain = URL("https://www.tokyomotion.net")
        self.request_limiter = AsyncLimiter(10, 1)
        self.next_page_selector = 'a.prevnext'
        self.title_selector = 'meta[property="og:title"]'
        self.next_page_attribute = "href"
        self.video_selector = 'a[href^="/video/"]'

    """~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""

    async def fetch(self, scrape_item: ScrapeItem) -> None:
        """Determines where to send the scrape item based on the url"""
        task_id = await self.scraping_progress.add_task(scrape_item.url)
        scrape_item.url = self.primary_base_domain.with_path(scrape_item.url.path)

        if 'video' in scrape_item.url.parts:
            await self.video(scrape_item)

        elif 'videos' in scrape_item.url.parts:
            await self.playlist(scrape_item)

        elif 'photo' in scrape_item.url.parts:
            await self.photo(scrape_item)

        elif any(part in scrape_item.url.parts for part in ('albums','photos')):
            await self.album(scrape_item)

        elif 'user' in scrape_item.url.parts:
            await self.profile(scrape_item)

        else:
            await self.search(scrape_item)

        await self.scraping_progress.remove_task(task_id)

    @error_handling_wrapper
    async def video(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a video"""
        if await self.check_complete_from_referer(scrape_item):
            return
        async with self.request_limiter:
            soup: BeautifulSoup = await self.client.get_BS4(self.domain, scrape_item.url)
        try:
            srcSD = soup.select_one('source[title="SD"]')
            srcHD = soup.select_one('source[title="HD"]')
            src = (srcHD or srcSD).get('src')
            link = URL(src)
        except AttributeError:
            if "This is a private video" in soup.text:
                raise ScrapeFailure('Private Video', f"Private video: {scrape_item.url}")
            raise ScrapeFailure(404, f"Could not find video source for {scrape_item.url}")
        
        title = soup.select_one('title').text.rsplit(" - TOKYO Motion")[0].strip()
       
        # NOTE: hardcoding the extension to prevent quering the final server URL
        # final server URL is always diferent so it can not be saved to db.
        filename, ext = scrape_item.url.parts[2], '.mp4'
        custom_file_name, _ = await get_filename_and_ext(f"{title} [{filename}]{ext}")
        await self.handle_file(link, scrape_item, filename, ext, custom_file_name)

    @error_handling_wrapper
    async def album(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        raise NotImplementedError
    
    @error_handling_wrapper
    async def photo(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        raise NotImplementedError
    
    @error_handling_wrapper
    async def profile(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        raise NotImplementedError
    
    @error_handling_wrapper
    async def search(self, scrape_item: ScrapeItem) -> None:
        """Scrapes an album"""
        raise NotImplementedError
    
    @error_handling_wrapper
    async def playlist(self, scrape_item: ScrapeItem) -> None:
        """Scrapes a video playlist"""
        title = 'favorites' if 'favorite' in scrape_item.url.parts else "videos" 
        user = scrape_item.url.parts[2]
        if user not in scrape_item.parent_title.split('/'):
            await scrape_item.add_to_parent_title(scrape_item.url.parts[2])

        async for soup in self.web_pager(scrape_item.url):
            videos = soup.select(self.video_selector)
            for video in videos:
                link = video.get('href')
                if not link:
                    continue

                if link.startswith("/"):
                    link = self.primary_base_domain / link[1:]

                link = URL(link)
                new_scrape_item = await self.create_scrape_item(scrape_item, link, new_title_part=title, add_parent = scrape_item.url)
                await self.video(new_scrape_item)

    async def web_pager(self, url: URL) -> AsyncGenerator[BeautifulSoup]:
        "Generator of website pages"
        page_url = url
        while True:
            async with self.request_limiter:
                soup: BeautifulSoup = await self.client.get_BS4(self.domain, page_url)
            next_page = soup.select_one(self.next_page_selector)
            yield soup
            if next_page :
                page_url = next_page.get(self.next_page_attribute)
                if page_url:
                    if page_url.startswith("/"):
                        page_url = self.primary_base_domain / page_url[1:]
                    page_url = URL(page_url)
                    continue
                break
