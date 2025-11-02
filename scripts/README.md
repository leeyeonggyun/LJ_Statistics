# 채널 ID 수집 스크립트

## 개요

YouTube API 할당량을 절약하기 위해 채널 이름 대신 채널 ID를 사용합니다.

- **채널 이름 검색**: 100 유닛/채널 × 90개 = 9,000 유닛
- **채널 ID 사용**: 1 유닛/50채널 × 90개 = 약 2 유닛

이 스크립트는 **단 한 번만** 실행하여 채널 ID를 수집하면 됩니다.

## 사용 방법

### 1. YouTube API 할당량 확인

[Google Cloud Console](https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas)에서 현재 할당량을 확인하세요.

- 하루 할당량: 10,000 유닛
- 필요 유닛: 약 9,000 유닛

**할당량이 부족하면 내일 리셋될 때까지 기다리세요!**

### 2. 스크립트 실행

```bash
cd /Users/yeonggyun/LJStatistics_Backend/yt-analytics-fastapi-starter
python scripts/collect_channel_ids.py
```

### 3. 결과 복사

스크립트가 완료되면 다음과 같은 형식으로 결과가 출력됩니다:

```python
CHANNEL_IDS = {
    "KR": [
        "UCiVs2pnGW5mLIc1jS2nxhjg",  # 김프로KIMPRO
        "UCOmHUn--16B90oW2L6FRR3A",  # BLACKPINK
        ...
    ],
    "JP": [...],
    "US": [...],
}
```

이 결과를 복사하여 `app/services/channel_names.py` 파일의 `CHANNEL_IDS` 부분에 붙여넣으세요.

### 4. 배포

```bash
git add app/services/channel_names.py
git commit -m "채널 ID 추가"
git push
```

## 주의사항

- 이 스크립트는 약 9,000 API 유닛을 사용합니다
- 할당량 초과 시 403 Forbidden 에러가 발생합니다
- 한 번 실행 후 결과를 저장하면 다시 실행할 필요 없습니다
- 채널 ID는 변경되지 않으므로 영구적으로 사용 가능합니다

## 문제 해결

### 403 Forbidden 에러

할당량이 초과된 경우입니다. 내일 (UTC 기준 자정) 리셋될 때까지 기다리세요.

### 채널을 찾을 수 없음

- 채널 이름이 정확한지 확인하세요
- 채널이 삭제되었거나 비공개일 수 있습니다
- 수동으로 YouTube에서 채널을 찾아 ID를 복사할 수 있습니다

채널 ID는 YouTube 채널 URL에서 확인할 수 있습니다:
- `https://www.youtube.com/channel/UCiVs2pnGW5mLIc1jS2nxhjg` → `UCiVs2pnGW5mLIc1jS2nxhjg`
