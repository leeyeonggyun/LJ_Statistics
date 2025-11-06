# YouTube 채널 검색 및 분석 서비스

FastAPI 기반 YouTube 채널 검색 및 국가별 인기 채널 순위 제공 서비스입니다.

## 주요 기능

### 1. 채널 검색
- 키워드 기반 YouTube 채널 검색
- 검색 결과 데이터베이스 캐싱 (날짜별)
- 구독자 수, 국가별 필터링 (클라이언트 사이드)
- 동일 날짜 동일 검색어는 API 호출 없이 DB에서 조회

### 2. 국가별 인기 채널 순위
- 한국(KR), 일본(JP), 미국(US) 3개국 지원
- 매월 1일 오전 0시 1분(KST) 자동 업데이트
- Redis 캐싱으로 빠른 응답 속도
- 데이터가 없을 경우 자동으로 업데이트

### 3. 자동 스케줄링
- APScheduler를 이용한 월별 자동 업데이트
- 한국 시간대(Asia/Seoul) 기준
- YouTube API 할당량 최적화

## 기술 스택

- **Backend**: FastAPI 0.115+
- **Database**: PostgreSQL (AsyncPG)
- **Cache**: Redis
- **Scheduler**: APScheduler
- **HTTP Client**: httpx
- **ORM**: SQLAlchemy 2.0+ (Async)

## 설치 및 실행

### 환경 변수 설정

`.env` 파일 생성:

```env
YOUTUBE_API_KEY=your_youtube_api_key
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

### 로컬 실행

```bash
pip install -e .

uvicorn app.main:app --reload
```

서버는 `http://localhost:8000`에서 실행됩니다.

## API 엔드포인트

### 채널 검색
```
GET /api/search/channels?q=검색어&max_results=100
```

**응답 예시:**
```json
{
  "query": "캠핑",
  "result_count": 100,
  "channels": [
    {
      "channelId": "UC...",
      "title": "채널명",
      "description": "설명",
      "thumbnailUrl": "https://...",
      "subscriberCount": 1000000,
      "videoCount": 500,
      "viewCount": 50000000,
      "customUrl": "@channel",
      "country": "KR",
      "publishedAt": "2020-01-01T00:00:00Z"
    }
  ]
}
```

### 국가별 순위 조회
```
GET /api/top-channels
```

**응답 예시:**
```json
{
  "KR": [...],
  "JP": [...],
  "US": [...]
}
```

### 헬스체크
```
GET /health
```

## 배포

### Coolify 자동 배포
- GitHub main 브랜치에 푸시 시 자동 배포
- 환경 변수는 Coolify 대시보드에서 설정

## 프로젝트 구조

```
app/
├── api/
│   └── endpoints/          # API 엔드포인트
│       ├── health.py
│       ├── search.py
│       └── top_channels.py
├── core/                   # 핵심 설정
│   ├── database.py         # DB 연결
│   ├── redis.py            # Redis 연결
│   ├── scheduler.py        # 스케줄러 설정
│   ├── settings.py         # 환경 변수
│   └── logging.py          # 로깅 설정
├── models/                 # 데이터베이스 모델
│   ├── search_result.py
│   └── top_channel.py
├── services/               # 비즈니스 로직
│   ├── youtube_client.py   # YouTube API 클라이언트
│   ├── search_service.py   # 검색 서비스
│   ├── top_channels_service.py
│   ├── channel_names.py    # 채널 ID 목록
│   └── utils.py            # 유틸리티
├── static/                 # 정적 파일
│   └── index.html          # 프론트엔드 UI
└── main.py                 # 애플리케이션 진입점
```

## 성능 최적화

### API 호출 최적화
- 채널 검색: 1페이지 (50개)
- 비디오 검색: 2페이지 (100개)
- 한 번의 검색당 약 4-5 API 호출
- 이전 대비 75-80% API 호출 감소

### 캐싱 전략
- 검색 결과: 7일간 데이터베이스 저장
- 국가별 순위: Redis 월별 캐싱
- 동일 검색어/날짜 조합 시 API 호출 없음

## 라이선스

MIT
