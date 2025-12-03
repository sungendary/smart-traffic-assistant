"""
특정 사용자 계정에 챌린지 장소 3개를 인증된 상태로 만드는 스크립트
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from bson import ObjectId

from app.core.config import settings
from app.db.mongo import MongoConnectionManager
from app.services.users import find_user_by_email
from app.services.challenge_places import list_challenge_places

USERS_COL = "users"
COUPLES_COL = "couples"
VISITS_COL = "visits"
CHALLENGE_PLACES_COL = "challenge_places"


async def verify_challenges_for_user(email: str, num_places: int = 3):
    """
    특정 사용자 계정에 챌린지 장소를 인증된 상태로 만듭니다.
    
    Args:
        email: 사용자 이메일
        num_places: 인증할 챌린지 장소 개수 (기본값: 3)
    """
    client = MongoConnectionManager.get_client()
    db = client[settings.mongodb_db]
    
    print(f"사용자 '{email}'의 챌린지 인증 상태를 업데이트합니다...\n")
    
    # 1단계: 사용자 찾기
    print("=" * 50)
    print("1단계: 사용자 찾기")
    print("=" * 50)
    user_doc = await find_user_by_email(db, email)
    if not user_doc:
        print(f"  ✗ 사용자를 찾을 수 없습니다: {email}")
        return
    
    user_id = user_doc["_id"]
    couple_id = user_doc.get("couple_id")
    
    if not couple_id:
        print(f"  ✗ 사용자에게 연결된 커플이 없습니다.")
        print(f"  → 커플을 먼저 생성하거나 가입해야 합니다.")
        return
    
    print(f"  ✓ 사용자 찾음 (ID: {user_id})")
    print(f"  ✓ 커플 ID: {couple_id}")
    
    # 2단계: 챌린지 장소 목록 가져오기
    print("\n" + "=" * 50)
    print("2단계: 챌린지 장소 목록 조회")
    print("=" * 50)
    
    # 활성화된 챌린지 장소 목록 가져오기
    challenge_places = await list_challenge_places(db, active_only=True)
    
    if not challenge_places:
        print("  ✗ 활성화된 챌린지 장소가 없습니다.")
        return
    
    print(f"  ✓ 총 {len(challenge_places)}개의 챌린지 장소를 찾았습니다.")
    
    # 이미 인증된 장소 확인
    couple_obj_id = ObjectId(couple_id)
    verified_places = []
    async for visit in db[VISITS_COL].find({
        "couple_id": couple_obj_id,
        "location_verified": True,
        "challenge_place_id": {"$ne": None}
    }):
        if visit.get("challenge_place_id"):
            verified_places.append(str(visit["challenge_place_id"]))
    
    print(f"  → 이미 인증된 장소: {len(verified_places)}개")
    
    # 3단계: 인증할 장소 선택 (이미 인증되지 않은 것 중에서)
    print("\n" + "=" * 50)
    print(f"3단계: {num_places}개 장소 인증")
    print("=" * 50)
    
    places_to_verify = []
    for place in challenge_places:
        place_id = place["id"]
        if place_id not in verified_places:
            places_to_verify.append(place)
            if len(places_to_verify) >= num_places:
                break
    
    if len(places_to_verify) < num_places:
        print(f"  ⚠ 인증 가능한 장소가 {len(places_to_verify)}개뿐입니다. (요청: {num_places}개)")
    
    # 4단계: visits 문서 생성/업데이트
    now = datetime.utcnow()
    verified_count = 0
    
    for place in places_to_verify:
        place_obj_id = ObjectId(place["id"])
        place_name = place.get("name", "알 수 없는 장소")
        
        # 기존 방문 기록 확인
        existing_visit = await db[VISITS_COL].find_one({
            "couple_id": couple_obj_id,
            "challenge_place_id": place_obj_id
        })
        
        if existing_visit:
            # 기존 기록 업데이트
            await db[VISITS_COL].update_one(
                {"_id": existing_visit["_id"]},
                {
                    "$set": {
                        "location_verified": True,
                        "updated_at": now
                    }
                }
            )
            print(f"  ✓ {place_name}: 기존 기록 업데이트 (인증 완료)")
        else:
            # 새 방문 기록 생성
            visit_doc = {
                "couple_id": couple_obj_id,
                "user_id": user_id,
                "plan_id": None,
                "place_id": place.get("place_id", ""),
                "place_name": place_name,
                "visited_at": now.isoformat(),
                "emotion": None,
                "tags": place.get("tags", []),
                "memo": "",
                "rating": None,
                "challenge_place_id": place_obj_id,
                "location_verified": True,
                "review_completed": False,
                "created_at": now,
                "updated_at": now,
            }
            await db[VISITS_COL].insert_one(visit_doc)
            print(f"  ✓ {place_name}: 새 기록 생성 (인증 완료)")
        
        verified_count += 1
    
    print("\n" + "=" * 50)
    print("인증 완료!")
    print("=" * 50)
    print(f"총 {verified_count}개의 챌린지 장소가 인증되었습니다.")
    
    # 최종 상태 확인
    final_verified = []
    async for visit in db[VISITS_COL].find({
        "couple_id": couple_obj_id,
        "location_verified": True,
        "challenge_place_id": {"$ne": None}
    }):
        if visit.get("challenge_place_id"):
            place_doc = await db[CHALLENGE_PLACES_COL].find_one({"_id": visit["challenge_place_id"]})
            if place_doc:
                final_verified.append(place_doc.get("name", "알 수 없는 장소"))
    
    print(f"\n현재 인증된 챌린지 장소 목록:")
    for i, name in enumerate(final_verified, 1):
        print(f"  {i}. {name}")


if __name__ == "__main__":
    # 사용자 이메일과 인증할 장소 개수
    email = "zhffkwhdk0@gmail.com"
    num_places = 3
    
    if len(sys.argv) > 1:
        email = sys.argv[1]
    if len(sys.argv) > 2:
        num_places = int(sys.argv[2])
    
    asyncio.run(verify_challenges_for_user(email, num_places))

