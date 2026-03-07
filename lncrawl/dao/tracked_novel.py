from typing import Optional

import sqlmodel as sa

from ._base import BaseTable


class TrackedNovel(BaseTable, table=True):
    __tablename__ = "tracked_novels"

    user_id: str = sa.Field(
        foreign_key="users.id",
        ondelete="CASCADE",
        index=True,
    )
    novel_id: Optional[str] = sa.Field(
        default=None,
        foreign_key="novels.id",
        ondelete="SET NULL",
        index=True,
    )
    novel_url: str = sa.Field(index=True)
    title: str = sa.Field(default="")
    domain: str = sa.Field(default="")
    last_known_chapters: int = sa.Field(default=0)
    last_checked_at: Optional[int] = sa.Field(
        default=None,
        sa_type=sa.BigInteger,
    )
    is_active: bool = sa.Field(default=True, index=True)
    is_complete: bool = sa.Field(default=False)
    check_interval_minutes: int = sa.Field(default=30)
    auto_download: bool = sa.Field(default=True)
    output_format: str = sa.Field(default="epub")
    last_error: Optional[str] = sa.Field(default=None)

    __table_args__ = (
        sa.Index("ix_tracked_novels_active", "is_active", "last_checked_at"),
        sa.UniqueConstraint("user_id", "novel_url", name="uq_tracked_user_novel"),
    )
