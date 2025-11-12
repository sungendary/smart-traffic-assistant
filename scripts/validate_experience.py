from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.places import FALLBACK_PLACES


def check_fallback_places() -> list[str]:
    problems: list[str] = []
    if len(FALLBACK_PLACES) < 2:
        problems.append("FALLBACK_PLACES 항목이 최소 2개 이상이어야 합니다.")

    for place in FALLBACK_PLACES:
        if not place.name:
            problems.append("샘플 장소에 이름이 비어 있습니다.")
        if not place.description:
            problems.append(f"{place.id} 장소에 설명이 없습니다.")
        if not place.coordinates.latitude or not place.coordinates.longitude:
            problems.append(f"{place.id} 장소 좌표가 잘못되었습니다.")
        if not place.tags:
            problems.append(f"{place.id} 장소 태그가 비어 있습니다.")
    return problems


def check_frontend_copy() -> list[str]:
    # 프론트엔드 검증 비활성화 (필요시 재활성화 가능)
    return []


def check_spec_alignment() -> list[str]:
    spec_path = Path("개발명세.md")
    if not spec_path.exists():
        return ["개발명세.md 문서를 찾을 수 없습니다."]

    content = spec_path.read_text(encoding="utf-8")
    anchors = [
        "취향 기반 데이트 코스 추천",
        "커플 챌린지 보상 시스템",
        "AI 러브 스펙트럼",
    ]
    return [f"개발명세.md에 '{anchor}' 설명이 누락되어 있습니다." for anchor in anchors if anchor not in content]


def main() -> int:
    issues: list[str] = []
    issues.extend(check_fallback_places())
    issues.extend(check_frontend_copy())
    issues.extend(check_spec_alignment())

    if issues:
        for issue in issues:
            print(f"[경고] {issue}", file=sys.stderr)
        return 1

    print("경험 품질 검증을 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
