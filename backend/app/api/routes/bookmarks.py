from fastapi import APIRouter, Depends, Path
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...dependencies import get_mongo_db
from ...schemas import BookmarkCreate, BookmarkOut, UserPublic
from ...services.bookmarks import add_bookmark, list_bookmarks, remove_bookmark
from ...services.couples import get_or_create_couple

router = APIRouter()


@router.get("/", response_model=list[BookmarkOut])
async def get_bookmarks(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> list[BookmarkOut]:
    couple = await get_or_create_couple(db, current_user.id)
    bookmarks = await list_bookmarks(db, str(couple["_id"]))
    return [BookmarkOut(**b) for b in bookmarks]


@router.post("/", response_model=BookmarkOut)
async def create_bookmark(
    payload: BookmarkCreate,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> BookmarkOut:
    couple = await get_or_create_couple(db, current_user.id)
    bookmark = await add_bookmark(db, str(couple["_id"]), current_user.id, payload.model_dump())
    return BookmarkOut(**bookmark)


@router.delete("/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: str = Path(..., description="북마크 ID"),
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> dict:
    couple = await get_or_create_couple(db, current_user.id)
    await remove_bookmark(db, bookmark_id, str(couple["_id"]))
    return {"status": "deleted"}
