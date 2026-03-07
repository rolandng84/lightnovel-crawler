import logging
from threading import Event
from typing import List, Optional

import sqlmodel as sq

from ..context import ctx
from ..dao.tracked_novel import TrackedNovel
from ..utils.time_utils import current_timestamp

logger = logging.getLogger(__name__)


class WatcherService:
    def list(
        self,
        user_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[List[TrackedNovel], int]:
        with ctx.db.session() as sess:
            stmt = sq.select(TrackedNovel)
            count_stmt = sq.select(sq.func.count()).select_from(TrackedNovel)

            if user_id is not None:
                stmt = stmt.where(TrackedNovel.user_id == user_id)
                count_stmt = count_stmt.where(TrackedNovel.user_id == user_id)
            if is_active is not None:
                stmt = stmt.where(TrackedNovel.is_active == is_active)
                count_stmt = count_stmt.where(TrackedNovel.is_active == is_active)

            total = sess.exec(count_stmt).one()
            items = sess.exec(
                stmt.order_by(TrackedNovel.updated_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            return list(items), total

    def get(self, tracked_id: str) -> Optional[TrackedNovel]:
        with ctx.db.session() as sess:
            return sess.get(TrackedNovel, tracked_id)

    def add(
        self,
        user_id: str,
        novel_url: str,
        check_interval_minutes: int = 30,
        auto_download: bool = True,
        output_format: str = "epub",
    ) -> TrackedNovel:
        from ..utils.url_tools import extract_host

        domain = extract_host(novel_url) or ""

        # Check if already tracked by this user
        with ctx.db.session() as sess:
            existing = sess.exec(
                sq.select(TrackedNovel).where(
                    TrackedNovel.user_id == user_id,
                    TrackedNovel.novel_url == novel_url,
                )
            ).first()
            if existing:
                existing.is_active = True
                sess.add(existing)
                sess.commit()
                sess.refresh(existing)
                return existing

            # Check if novel already exists in DB
            from ..dao.novel import Novel

            novel = sess.exec(
                sq.select(Novel).where(Novel.url == novel_url)
            ).first()

            tracked = TrackedNovel(
                user_id=user_id,
                novel_url=novel_url,
                domain=domain,
                title=novel.title if novel else "",
                novel_id=novel.id if novel else None,
                last_known_chapters=novel.chapter_count if novel else 0,
                check_interval_minutes=check_interval_minutes,
                auto_download=auto_download,
                output_format=output_format,
            )
            sess.add(tracked)
            sess.commit()
            sess.refresh(tracked)
            return tracked

    def update(self, tracked_id: str, **kwargs) -> Optional[TrackedNovel]:
        with ctx.db.session() as sess:
            tracked = sess.get(TrackedNovel, tracked_id)
            if not tracked:
                return None
            for key, value in kwargs.items():
                if hasattr(tracked, key) and key not in ("id", "user_id", "created_at"):
                    setattr(tracked, key, value)
            sess.add(tracked)
            sess.commit()
            sess.refresh(tracked)
            return tracked

    def delete(self, tracked_id: str) -> bool:
        with ctx.db.session() as sess:
            tracked = sess.get(TrackedNovel, tracked_id)
            if not tracked:
                return False
            sess.delete(tracked)
            sess.commit()
            return True

    def check_novel(self, tracked: TrackedNovel, signal: Event) -> None:
        """Check a single tracked novel for new chapters."""
        try:
            novel = ctx.crawler.fetch_novel(
                tracked.user_id,
                tracked.novel_url,
                signal=signal,
            )

            with ctx.db.session() as sess:
                t = sess.get(TrackedNovel, tracked.id)
                if not t:
                    return

                t.novel_id = novel.id
                t.title = novel.title
                t.last_checked_at = current_timestamp()
                t.last_error = None

                new_chapters = novel.chapter_count - t.last_known_chapters

                if new_chapters > 0:
                    logger.info(
                        f"[Watcher] {novel.title}: {new_chapters} new chapters "
                        f"({t.last_known_chapters} -> {novel.chapter_count})"
                    )
                    t.last_known_chapters = novel.chapter_count

                    if t.auto_download:
                        self._create_download_job(t, novel, new_chapters)
                elif new_chapters == 0:
                    logger.debug(f"[Watcher] {novel.title}: no new chapters")
                else:
                    logger.warning(
                        f"[Watcher] {novel.title}: chapter count decreased "
                        f"({t.last_known_chapters} -> {novel.chapter_count})"
                    )
                    t.last_known_chapters = novel.chapter_count

                sess.add(t)
                sess.commit()

        except Exception as e:
            logger.error(f"[Watcher] Error checking {tracked.novel_url}: {e}")
            with ctx.db.session() as sess:
                t = sess.get(TrackedNovel, tracked.id)
                if t:
                    t.last_error = str(e)[:500]
                    t.last_checked_at = current_timestamp()
                    sess.add(t)
                    sess.commit()

    def _create_download_job(self, tracked: TrackedNovel, novel, new_chapters: int):
        """Create a job to download new chapters and generate artifact."""
        try:
            from ..dao.user import User

            with ctx.db.session() as sess:
                user = sess.get(User, tracked.user_id)
                if not user:
                    return

            # Create a full novel fetch job (re-fetches chapters + generates artifact)
            job = ctx.jobs.fetch_novel(user, tracked.novel_url, full=True)
            logger.info(
                f"[Watcher] Created job {job.id} for {novel.title} "
                f"({new_chapters} new chapters)"
            )
        except Exception as e:
            logger.error(f"[Watcher] Failed to create job: {e}")

    def run_check(self, signal: Event) -> None:
        """Check all active tracked novels that are due."""
        now = current_timestamp()

        with ctx.db.session() as sess:
            items = sess.exec(
                sq.select(TrackedNovel).where(
                    TrackedNovel.is_active == True,  # noqa: E712
                    TrackedNovel.is_complete == False,  # noqa: E712
                )
            ).all()

        for tracked in items:
            if signal.is_set():
                return

            # Check if enough time has passed since last check
            if tracked.last_checked_at:
                elapsed_ms = now - tracked.last_checked_at
                interval_ms = tracked.check_interval_minutes * 60 * 1000
                if elapsed_ms < interval_ms:
                    continue

            logger.info(f"[Watcher] Checking {tracked.title or tracked.novel_url}")
            self.check_novel(tracked, signal)
