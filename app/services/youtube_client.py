
import httpx
import asyncio
from typing import Any, Dict, List, Optional
from .utils import backoff_client
from app.core.settings import settings

BASE = "https://www.googleapis.com/youtube/v3"

async def get_i18n_regions() -> List[Dict[str, str]]:
    async with backoff_client() as client:
        params = {
            "part": "snippet",
            "key": settings.youtube_api_key,
        }

        response = await client.get(f"{BASE}/i18nRegions", params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        regions = []
        for item in data.get("items", []):
            regions.append({
                "code": item["snippet"]["gl"],
                "name": item["snippet"]["name"]
            })

        return regions

async def search_videos_recent_week(q: str, max_results: int = 25) -> Dict[str, Any]:
    params = {
        "q": q,
        "part": "id,snippet",
        "type": "video",
        "order": "viewCount",
        "maxResults": max_results,
        "key": settings.youtube_api_key,
    }
    async with backoff_client() as client:
        r = await client.get(f"{BASE}/search", params=params, timeout=20)
        r.raise_for_status()
        return r.json()

async def get_trending_channels(region_code: str = "KR", max_results: int = 50) -> Dict[str, Any]:
    async with backoff_client() as client:
        all_channels_dict = {}
        next_page_token = None
        pages_to_fetch = 3

        for page in range(pages_to_fetch):
            videos_params = {
                "part": "snippet",
                "chart": "mostPopular",
                "regionCode": region_code,
                "maxResults": 50,
                "key": settings.youtube_api_key,
            }

            if next_page_token:
                videos_params["pageToken"] = next_page_token

            videos_response = await client.get(f"{BASE}/videos", params=videos_params, timeout=20)
            videos_response.raise_for_status()
            videos_data = videos_response.json()

            items = videos_data.get("items", [])
            if not items:
                break

            for item in items:
                channel_id = item["snippet"]["channelId"]
                all_channels_dict[channel_id] = all_channels_dict.get(channel_id, 0) + 1

            next_page_token = videos_data.get("nextPageToken")
            if not next_page_token:
                break

        if not all_channels_dict:
            return {"channels": [], "regionCode": region_code}

        channel_ids = list(all_channels_dict.keys())
        all_channels = []
        batch_size = 50

        for i in range(0, len(channel_ids), batch_size):
            batch_ids = channel_ids[i:i + batch_size]
            channels_params = {
                "part": "snippet,statistics",
                "id": ",".join(batch_ids),
                "key": settings.youtube_api_key,
            }

            channels_response = await client.get(f"{BASE}/channels", params=channels_params, timeout=20)
            channels_response.raise_for_status()
            channels_data = channels_response.json()
            all_channels.extend(channels_data.get("items", []))

        results = []
        for channel in all_channels:
            channel_country = channel["snippet"].get("country", "")

            if channel_country != region_code:
                continue

            subscriber_count = int(channel["statistics"].get("subscriberCount", 0))
            video_count = int(channel["statistics"].get("videoCount", 0))
            view_count = int(channel["statistics"].get("viewCount", 0))

            results.append({
                "channelId": channel["id"],
                "title": channel["snippet"]["title"],
                "description": channel["snippet"]["description"],
                "thumbnailUrl": channel["snippet"]["thumbnails"]["default"]["url"],
                "subscriberCount": subscriber_count,
                "videoCount": video_count,
                "viewCount": view_count,
                "customUrl": channel["snippet"].get("customUrl", ""),
                "country": channel_country,
                "publishedAt": channel["snippet"].get("publishedAt", ""),
                "videoAppearances": all_channels_dict.get(channel["id"], 0)
            })

        results.sort(key=lambda x: (x["videoAppearances"], x["subscriberCount"]), reverse=True)
        results = results[:max_results]

        return {
            "channels": results,
            "regionCode": region_code
        }


async def search_channel_by_name(channel_name: str) -> Optional[str]:
    async with backoff_client() as client:
        search_params = {
            "part": "snippet",
            "q": channel_name,
            "type": "channel",
            "maxResults": 10,
            "key": settings.youtube_api_key,
        }

        try:
            response = await client.get(f"{BASE}/search", params=search_params, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])

            for item in items:
                item_title = item["snippet"]["title"]
                if item_title == channel_name:
                    return item["id"]["channelId"]

            for item in items:
                item_title = item["snippet"]["title"]
                if item_title.lower() == channel_name.lower():
                    return item["id"]["channelId"]

            return None

        except Exception:
            pass

        return None


async def get_channels_by_ids(channel_ids: List[str]) -> List[Dict[str, Any]]:
    if not channel_ids:
        return []

    async with backoff_client() as client:
        batch_size = 50

        batches = []
        for i in range(0, len(channel_ids), batch_size):
            batch_ids = channel_ids[i:i + batch_size]
            batches.append(batch_ids)

        async def fetch_batch(batch_ids):
            channels_params = {
                "part": "snippet,statistics",
                "id": ",".join(batch_ids),
                "key": settings.youtube_api_key,
            }
            channels_response = await client.get(f"{BASE}/channels", params=channels_params, timeout=20)
            channels_response.raise_for_status()
            channels_data = channels_response.json()
            return channels_data.get("items", [])

        batch_results = await asyncio.gather(*[fetch_batch(batch) for batch in batches], return_exceptions=True)

        all_channels_data = []
        for result in batch_results:
            if isinstance(result, list):
                all_channels_data.extend(result)
            elif isinstance(result, Exception):
                pass

        channels = []
        for channel in all_channels_data:
            subscriber_count = int(channel["statistics"].get("subscriberCount", 0))
            video_count = int(channel["statistics"].get("videoCount", 0))
            view_count = int(channel["statistics"].get("viewCount", 0))

            channels.append({
                "channelId": channel["id"],
                "title": channel["snippet"]["title"],
                "description": channel["snippet"]["description"],
                "thumbnailUrl": channel["snippet"]["thumbnails"]["default"]["url"],
                "subscriberCount": subscriber_count,
                "videoCount": video_count,
                "viewCount": view_count,
                "customUrl": channel["snippet"].get("customUrl", ""),
                "publishedAt": channel["snippet"].get("publishedAt", ""),
            })

        channels.sort(key=lambda x: x["subscriberCount"], reverse=True)
        return channels


async def get_channels_by_names(channel_names: List[str]) -> List[Dict[str, Any]]:
    search_tasks = [search_channel_by_name(name) for name in channel_names]
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    channel_ids = []
    for result in search_results:
        if isinstance(result, str):
            channel_ids.append(result)
        elif isinstance(result, Exception):
            pass

    return await get_channels_by_ids(channel_ids)


async def get_top_channels_by_country(country_code: str, top_n: int = 5) -> List[Dict[str, Any]]:
    async with backoff_client() as client:
        all_channel_ids = set()
        page_token = None
        pages_to_fetch = 3

        for page in range(pages_to_fetch):
            videos_params = {
                "part": "snippet",
                "chart": "mostPopular",
                "regionCode": country_code,
                "maxResults": 50,
                "key": settings.youtube_api_key,
            }

            if page_token:
                videos_params["pageToken"] = page_token

            videos_response = await client.get(f"{BASE}/videos", params=videos_params, timeout=20)
            videos_response.raise_for_status()
            videos_data = videos_response.json()

            items = videos_data.get("items", [])
            if not items:
                break

            for item in items:
                channel_id = item["snippet"]["channelId"]
                all_channel_ids.add(channel_id)

            page_token = videos_data.get("nextPageToken")
            if not page_token:
                break

        channel_ids = all_channel_ids

        if not channel_ids:
            return []

        all_channels_data = []
        channel_ids_list = list(channel_ids)
        batch_size = 50

        for i in range(0, len(channel_ids_list), batch_size):
            batch_ids = channel_ids_list[i:i + batch_size]
            channels_params = {
                "part": "snippet,statistics",
                "id": ",".join(batch_ids),
                "key": settings.youtube_api_key,
            }

            channels_response = await client.get(f"{BASE}/channels", params=channels_params, timeout=20)
            channels_response.raise_for_status()
            channels_data = channels_response.json()
            all_channels_data.extend(channels_data.get("items", []))

        channels = []
        for channel in all_channels_data:
            channel_country = channel["snippet"].get("country", "")

            if channel_country != country_code:
                continue

            subscriber_count = int(channel["statistics"].get("subscriberCount", 0))
            video_count = int(channel["statistics"].get("videoCount", 0))
            view_count = int(channel["statistics"].get("viewCount", 0))

            channels.append({
                "channelId": channel["id"],
                "title": channel["snippet"]["title"],
                "description": channel["snippet"]["description"],
                "thumbnailUrl": channel["snippet"]["thumbnails"]["default"]["url"],
                "subscriberCount": subscriber_count,
                "videoCount": video_count,
                "viewCount": view_count,
                "customUrl": channel["snippet"].get("customUrl", ""),
                "publishedAt": channel["snippet"].get("publishedAt", ""),
            })

        channels.sort(key=lambda x: x["subscriberCount"], reverse=True)
        return channels[:top_n]
