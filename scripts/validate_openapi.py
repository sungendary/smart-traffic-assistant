from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


def main() -> int:
    spec = app.openapi()
    paths = spec.get("paths", {})
    required_paths = [
        "/api/health",
        "/api/map/suggestions",
        "/api/reports/monthly",
    ]

    missing = [path for path in required_paths if path not in paths]
    if missing:
        for path in missing:
            print(f"[오류] OpenAPI 스펙에 {path} 경로가 없습니다.", file=sys.stderr)
        return 1

    print("OpenAPI 필수 경로 검증 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
