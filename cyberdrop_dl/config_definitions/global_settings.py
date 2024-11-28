from pydantic import BaseModel, ByteSize, Field, NonNegativeFloat, PositiveInt, field_serializer, field_validator
from yarl import URL
from datetime import timedelta
import humanfriendly

from .custom_types import AliasModel, HttpURL, NonEmptyStr


class General(BaseModel):
    allow_insecure_connections: bool = False
    user_agent: NonEmptyStr = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
    proxy: HttpURL | None = None
    flaresolverr: HttpURL | None = None
    max_file_name_length: PositiveInt = 95
    max_folder_name_length: PositiveInt = 60
    required_free_space: ByteSize = ByteSize._validate("5GB", "")

    @field_serializer("required_free_space")
    def human_readable(self, value: ByteSize | int) -> str:
        if not isinstance(value, ByteSize):
            value = ByteSize(value)
        return value.human_readable(decimal=True)

    @field_serializer("flaresolverr", "proxy")
    def convert_to_str(self, value: URL) -> str:
        if isinstance(value, URL):
            return str(value)
        return value


class RateLimitingOptions(BaseModel):
    connection_timeout: PositiveInt = 15
    download_attempts: PositiveInt = 5
    read_timeout: PositiveInt = 300
    rate_limit: PositiveInt = 50
    download_delay: NonNegativeFloat = 0.5
    max_simultaneous_downloads: PositiveInt = 15
    max_simultaneous_downloads_per_domain: PositiveInt = 3
    download_speed_limit: ByteSize = ByteSize(0)
    file_host_cache_length: timedelta = Field(default=timedelta(days=7))
    forum_cache_length: timedelta = Field(default=timedelta(days=28, hours=12, minutes=30, seconds=15, milliseconds=500, microseconds=250))

    @field_serializer("download_speed_limit")
    def human_readable(self, value: ByteSize | int) -> str:
        if not isinstance(value, ByteSize):
            value = ByteSize(value)
        return value.human_readable(decimal=True)

    @field_serializer("file_host_cache_length", "forum_cache_length")
    def serialize_timedelta(self, value: timedelta) -> str:
        return humanfriendly.format_timespan(value.total_seconds())

    @field_validator("file_host_cache_length", "forum_cache_length", mode="before")
    def parse_timedelta(cls, value):
        if isinstance(value, str):
            try:
                seconds = humanfriendly.parse_timespan(value)
                return timedelta(seconds=seconds)
            except humanfriendly.InvalidTimespan:
                raise ValueError(f"Invalid time span format: {value}")
        return value


class UIOptions(BaseModel):
    vi_mode: bool = False
    refresh_rate: PositiveInt = 10
    scraping_item_limit: PositiveInt = 5
    downloading_item_limit: PositiveInt = 5


class GlobalSettings(AliasModel):
    general: General = Field(validation_alias="General", default=General())
    rate_limiting_options: RateLimitingOptions = Field(
        validation_alias="Rate_Limiting_Options", default=RateLimitingOptions()
    )
    ui_options: UIOptions = Field(validation_alias="UI_Options", default=UIOptions())
