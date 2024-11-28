from __future__ import annotations

from dataclasses import field
from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from cyberdrop_dl.utils import yaml
from aiohttp_client_cache import SQLiteBackend

from cyberdrop_dl.scraper.filters import filter_fn
from cyberdrop_dl.utils.data_enums_classes.supported_domains import SupportedDomains

if TYPE_CHECKING:
    from pathlib import Path

    from cyberdrop_dl.managers.manager import Manager


class CacheManager:
    def __init__(self, manager: Manager) -> None:
        self.manager = manager

        self.request_cache: SQLiteBackend = field(init=False)
        self.cache_file: Path = field(init=False)
        self._cache = {}

    def startup(self, cache_file: Path) -> None:
        """Ensures that the cache file exists."""
        self.cache_file = cache_file
        if not self.cache_file.is_file():
            self.save("default_config", "Default")

        self.load()
        if self.manager.parsed_args.cli_only_args.appdata_folder:
            self.save("first_startup_completed", True)

    def load(self) -> None:
        """Loads the cache file into memory."""
        self._cache = yaml.load(self.cache_file)

    def load_request_cache(self) -> None:
        urls_expire_after = {
            "*.simpcity.su": self.manager.config_manager.global_settings_data.rate_limiting_options.file_host_cache_length,
        }
        for host in SupportedDomains.supported_hosts:
            urls_expire_after[f"*.{host}" if "." in host else f"*.{host}.*"] = (
                self.manager.config_manager.global_settings_data.rate_limiting_options.file_host_cache_length
            )
        for forum in SupportedDomains.supported_forums:
            urls_expire_after[f"{forum}"] = self.manager.config_manager.global_settings_data.rate_limiting_options.forum_cache_length
        self.request_cache = SQLiteBackend(
            cache_name=self.manager.path_manager.cache_db,
            autoclose=False,
            allowed_codes=(
                HTTPStatus.OK,
                HTTPStatus.NOT_FOUND,
                HTTPStatus.GONE,
                HTTPStatus.UNAVAILABLE_FOR_LEGAL_REASONS,
            ),
            allowed_methods=["GET"],
            expire_after=timedelta(days=7),
            urls_expire_after=urls_expire_after,
            filter_fn=filter_fn,
        )

    def get(self, key: str) -> Any:
        """Returns the value of a key in the cache."""
        return self._cache.get(key, None)

    def save(self, key: str, value: Any) -> None:
        """Saves a key and value to the cache."""
        self._cache[key] = value
        yaml.save(self.cache_file, self._cache)

    def remove(self, key: str) -> None:
        """Removes a key from the cache."""
        if key in self._cache:
            del self._cache[key]
            yaml.save(self.cache_file, self._cache)

    async def close(self):
        await self.request_cache.close()
