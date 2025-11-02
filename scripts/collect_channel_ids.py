#!/usr/bin/env python3
"""
채널 ID 수집 스크립트

이 스크립트는 한 번만 실행하면 됩니다.
YouTube API를 사용하여 채널 이름으로 채널 ID를 검색하고,
그 결과를 Python 코드 형식으로 출력합니다.

사용법:
    python scripts/collect_channel_ids.py

주의:
    - 이 스크립트는 약 9,000 API 유닛을 사용합니다
    - YouTube API 할당량이 충분한지 확인하세요 (하루 10,000 유닛)
    - 할당량 초과 시 내일 다시 실행하세요
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.youtube_client import search_channel_by_name
from app.services.channel_names import CHANNEL_NAMES


async def collect_ids_for_country(country_code: str, channel_names: list) -> dict:
    """수집된 채널 정보 반환 (이름, ID)"""
    results = []
    total = len(channel_names)

    print(f"\n{'='*60}")
    print(f"국가: {country_code} ({total}개 채널)")
    print(f"{'='*60}")

    for idx, name in enumerate(channel_names, 1):
        print(f"[{idx}/{total}] 검색 중: {name}... ", end='', flush=True)

        try:
            channel_id = await search_channel_by_name(name)

            if channel_id:
                print(f"✓ {channel_id}")
                results.append({
                    "name": name,
                    "id": channel_id
                })
            else:
                print(f"✗ 찾을 수 없음")
                results.append({
                    "name": name,
                    "id": None
                })

            # Avoid rate limiting
            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"✗ 오류: {e}")
            results.append({
                "name": name,
                "id": None
            })

    return results


async def main():
    print("="*60)
    print("YouTube 채널 ID 수집 스크립트")
    print("="*60)
    print(f"\n경고: 이 스크립트는 약 9,000 API 유닛을 사용합니다.")
    print(f"YouTube API 할당량이 충분한지 확인하세요.\n")

    input("계속하려면 Enter 키를 누르세요... ")

    all_results = {}

    for country_code in ["KR", "JP", "US"]:
        channel_names = CHANNEL_NAMES.get(country_code, [])

        if not channel_names:
            print(f"경고: {country_code}에 대한 채널 이름이 없습니다.")
            continue

        results = await collect_ids_for_country(country_code, channel_names)
        all_results[country_code] = results

    # Print results in Python code format
    print("\n" + "="*60)
    print("결과 (app/services/channel_names.py 에 복사하세요)")
    print("="*60 + "\n")

    print("CHANNEL_IDS = {")

    for country_code in ["KR", "JP", "US"]:
        if country_code not in all_results:
            continue

        print(f'    "{country_code}": [')

        for item in all_results[country_code]:
            name = item["name"]
            channel_id = item["id"]

            if channel_id:
                print(f'        "{channel_id}",  # {name}')
            else:
                print(f'        # NOT FOUND: {name}')

        print("    ],")

    print("}")

    # Print summary
    print("\n" + "="*60)
    print("요약")
    print("="*60)

    for country_code in ["KR", "JP", "US"]:
        if country_code not in all_results:
            continue

        total = len(all_results[country_code])
        found = sum(1 for item in all_results[country_code] if item["id"])
        not_found = total - found

        print(f"{country_code}: 총 {total}개, 찾음 {found}개, 못 찾음 {not_found}개")

    print("\n완료! 위의 CHANNEL_IDS를 app/services/channel_names.py 파일에 복사하세요.")


if __name__ == "__main__":
    asyncio.run(main())
