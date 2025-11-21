"""
수원특례시 내 챌린지 장소 초기 데이터 삽입 스크립트

데이팅 앱에 적합한 5가지 챌린지:
1. 로맨틱한 산책 코스 - 수원 화성 성곽길
2. 전통시장 미식 투어 - 수원 남문시장
3. 문화 예술 체험 - 수원시립아이파크미술관
4. 카페 데이트 - 행궁동 카ㅓ떻페거리
5. 야경 감상 - 광교호수공원
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.db.mongo import MongoConnectionManager
from app.services.challenge_places import create_challenge_place


# 수원특례시 내 챌린지 장소 데이터
CHALLENGE_PLACES = [
    {
        "name": "수원 화성 성곽길",
        "description": "유네스코 세계문화유산인 수원 화성을 따라 걷는 로맨틱한 산책 코스. 아름다운 경관과 역사적 의미를 함께 즐길 수 있습니다.",
        "latitude": 37.2886,  # 수원 화성 근처 좌표
        "longitude": 127.0123,
        "address": "경기도 수원시 팔달구 정조로 825",
        "tags": ["산책", "역사", "로맨틱", "야외"],
        "badge_reward": "🏛️",
        "points_reward": 500,
    },
    {
        "name": "수원 남문시장",
        "description": "다양한 전통 음식과 간식을 맛볼 수 있는 전통시장. 함께 시장을 탐방하며 미식 경험을 공유할 수 있습니다.",
        "latitude": 37.2806,
        "longitude": 127.0144,
        "address": "경기도 수원시 팔달구 남문로 92",
        "tags": ["음식", "시장", "전통", "미식"],
        "badge_reward": "🍜",
        "points_reward": 500,
    },
    {
        "name": "수원시립아이파크미술관",
        "description": "다양한 현대 미술 작품을 감상하며 예술적 감성을 나눌 수 있는 문화 공간입니다.",
        "latitude": 37.2633,
        "longitude": 127.0286,
        "address": "경기도 수원시 영통구 월드컵로 399",
        "tags": ["문화", "예술", "미술관", "실내"],
        "badge_reward": "🎨",
        "points_reward": 500,
    },
    {
        "name": "행궁동 카페거리",
        "description": "아기자기한 카페들이 모여 있는 거리. 다양한 분위기의 카페에서 여유로운 시간을 보낼 수 있습니다.",
        "latitude": 37.2861,
        "longitude": 127.0167,
        "address": "경기도 수원시 팔달구 행궁로",
        "tags": ["카페", "데이트", "실내", "힐링"],
        "badge_reward": "☕",
        "points_reward": 500,
    },
    {
        "name": "광교호수공원",
        "description": "호수 주변을 따라 산책하며 아름다운 야경을 감상할 수 있는 명소입니다.",
        "latitude": 37.2889,
        "longitude": 127.0511,
        "address": "경기도 수원시 영통구 광교호수로 142",
        "tags": ["야경", "공원", "산책", "로맨틱"],
        "badge_reward": "🌃",
        "points_reward": 500,
    },
]


async def init_challenge_places():
    """챌린지 장소 초기 데이터 삽입"""
    client = MongoConnectionManager.get_client()
    db = client[settings.mongodb_db]
    
    print("챌린지 장소 초기 데이터 삽입을 시작합니다...")
    
    for place_data in CHALLENGE_PLACES:
        # 이미 존재하는지 확인
        existing = await db["challenge_places"].find_one({"name": place_data["name"]})
        if existing:
            # 기존 데이터 업데이트 (위도/경도 포함)
            update_data = {
                "latitude": place_data["latitude"],
                "longitude": place_data["longitude"],
                "description": place_data["description"],
                "address": place_data["address"],
                "tags": place_data["tags"],
                "badge_reward": place_data["badge_reward"],
                "points_reward": place_data["points_reward"],
                "updated_at": datetime.utcnow()
            }
            await db["challenge_places"].update_one(
                {"name": place_data["name"]},
                {"$set": update_data}
            )
            print(f"  ✓ {place_data['name']}: 업데이트 완료 (ID: {existing['_id']})")
            continue
        
        # 챌린지 장소 생성
        try:
            result = await create_challenge_place(db, place_data)
            print(f"  ✓ {place_data['name']}: 생성 완료 (ID: {result['id']})")
        except Exception as e:
            print(f"  ✗ {place_data['name']}: 생성 실패 - {e}")
    
    print("\n챌린지 장소 초기 데이터 삽입이 완료되었습니다.")
    print(f"총 {len(CHALLENGE_PLACES)}개의 챌린지 장소가 준비되었습니다.")


if __name__ == "__main__":
    asyncio.run(init_challenge_places())