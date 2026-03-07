from typing import Optional

from fastapi import APIRouter, Body, Path, Query, Security

from ...context import ctx
from ...dao import TrackedNovel, User
from ..models.pagination import Paginated
from ..models.watcher import TrackNovelRequest, UpdateTrackedNovelRequest
from ..security import ensure_user

router = APIRouter()


@router.get("s", summary="List tracked novels")
def list_tracked(
    user: User = Security(ensure_user),
    offset: int = Query(default=0),
    limit: int = Query(default=50, le=100),
    is_active: Optional[bool] = Query(default=None),
) -> Paginated[TrackedNovel]:
    items, total = ctx.watcher.list(
        user_id=user.id,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return Paginated(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/all", summary="List all tracked novels (admin)")
def list_all_tracked(
    user: User = Security(ensure_user),
    offset: int = Query(default=0),
    limit: int = Query(default=50, le=100),
    is_active: Optional[bool] = Query(default=None),
) -> Paginated[TrackedNovel]:
    items, total = ctx.watcher.list(
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return Paginated(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("", summary="Track a novel for new chapters")
def track_novel(
    user: User = Security(ensure_user),
    body: TrackNovelRequest = Body(),
) -> TrackedNovel:
    return ctx.watcher.add(
        user_id=user.id,
        novel_url=str(body.novel_url),
        check_interval_minutes=body.check_interval_minutes,
        auto_download=body.auto_download,
        output_format=body.output_format,
    )


@router.get("/{tracked_id}", summary="Get a tracked novel")
def get_tracked(
    user: User = Security(ensure_user),
    tracked_id: str = Path(),
) -> TrackedNovel:
    tracked = ctx.watcher.get(tracked_id)
    if not tracked:
        from ...exceptions import ServerErrors
        raise ServerErrors.not_found
    return tracked


@router.patch("/{tracked_id}", summary="Update a tracked novel")
def update_tracked(
    user: User = Security(ensure_user),
    tracked_id: str = Path(),
    body: UpdateTrackedNovelRequest = Body(),
) -> TrackedNovel:
    updates = body.model_dump(exclude_none=True)
    tracked = ctx.watcher.update(tracked_id, **updates)
    if not tracked:
        from ...exceptions import ServerErrors
        raise ServerErrors.not_found
    return tracked


@router.delete("/{tracked_id}", summary="Stop tracking a novel")
def delete_tracked(
    user: User = Security(ensure_user),
    tracked_id: str = Path(),
) -> bool:
    return ctx.watcher.delete(tracked_id)


@router.post("/{tracked_id}/check", summary="Force check a tracked novel now")
def force_check(
    user: User = Security(ensure_user),
    tracked_id: str = Path(),
) -> TrackedNovel:
    from threading import Event

    tracked = ctx.watcher.get(tracked_id)
    if not tracked:
        from ...exceptions import ServerErrors
        raise ServerErrors.not_found

    ctx.watcher.check_novel(tracked, Event())

    # Return refreshed state
    return ctx.watcher.get(tracked_id)
