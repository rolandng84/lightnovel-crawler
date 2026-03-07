from typing import Optional

from pydantic import BaseModel


class TrackNovelRequest(BaseModel):
    novel_url: str
    check_interval_minutes: int = 30
    auto_download: bool = True
    output_format: str = "epub"


class UpdateTrackedNovelRequest(BaseModel):
    is_active: Optional[bool] = None
    check_interval_minutes: Optional[int] = None
    auto_download: Optional[bool] = None
    output_format: Optional[str] = None
