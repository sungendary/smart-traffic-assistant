from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...core.auth import get_current_user
from ...dependencies import get_mongo_db
from ...schemas import (
    CouplePreferences,
    CoupleSummary,
    InviteResponse,
    JoinRequest,
    PreferenceUpdate,
    UserPublic,
)
from ...services import users as user_service
from ...services.couples import calculate_tier, get_or_create_couple, join_couple_by_code, regenerate_invite_code, update_preferences

router = APIRouter()


def _serialize_couple(couple: dict, members: list[UserPublic]) -> CoupleSummary:
    prefs = couple.get("preferences", {})
    badges = couple.get("badges", [])
    badge_count = len(badges)
    tier_info = calculate_tier(badge_count)
    return CoupleSummary(
        id=str(couple["_id"]),
        invite_code=couple.get("invite_code", ""),
        members=members,
        preferences=CouplePreferences(**prefs),
        tier=tier_info["tier"],
        tier_name=tier_info["tier_name"],
        badge_count=badge_count,
    )


@router.get("/me", response_model=CoupleSummary)
async def get_my_couple(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> CoupleSummary:
    couple = await get_or_create_couple(db, current_user.id)
    members = []
    for user_id in couple.get("members", []):
        doc = await user_service.get_user_by_id(db, str(user_id))
        if doc:
            members.append(user_service.document_to_user(doc))
    return _serialize_couple(couple, members)


@router.post("/invite", response_model=InviteResponse)
async def regenerate_code(
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> InviteResponse:
    couple = await get_or_create_couple(db, current_user.id)
    code = await regenerate_invite_code(db, str(couple["_id"]))
    return InviteResponse(invite_code=code)


@router.post("/join", response_model=CoupleSummary)
async def join_with_code(
    payload: JoinRequest,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> CoupleSummary:
    couple = await join_couple_by_code(db, current_user.id, payload.code)
    members = []
    for user_id in couple.get("members", []):
        doc = await user_service.get_user_by_id(db, str(user_id))
        if doc:
            members.append(user_service.document_to_user(doc))
    return _serialize_couple(couple, members)


@router.patch("/preferences", response_model=CoupleSummary)
async def update_couple_preferences(
    payload: PreferenceUpdate,
    current_user: UserPublic = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> CoupleSummary:
    couple = await get_or_create_couple(db, current_user.id)
    updated = await update_preferences(db, str(couple["_id"]), payload.model_dump())
    members = []
    for user_id in updated.get("members", []):
        doc = await user_service.get_user_by_id(db, str(user_id))
        if doc:
            members.append(user_service.document_to_user(doc))
    return _serialize_couple(updated, members)
