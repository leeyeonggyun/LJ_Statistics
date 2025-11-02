
import httpx
import asyncio
from typing import Any, Dict, List, Optional
from .utils import backoff_client
from app.core.settings import settings

BASE = "https://www.googleapis.com/youtube/v3"

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

async def get_latest_upload_date(client: httpx.AsyncClient, uploads_playlist_id: str) -> Optional[str]:
    try:
        playlist_params = {
            "part": "snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": 1,
            "key": settings.youtube_api_key,
        }
        playlist_response = await client.get(f"{BASE}/playlistItems", params=playlist_params, timeout=10)
        playlist_response.raise_for_status()
        playlist_data = playlist_response.json()

        if playlist_data.get("items"):
            return playlist_data["items"][0]["snippet"]["publishedAt"]
    except Exception:
        pass
    return None


async def search_channels(q: str, max_results: int = 150, page_token: str = None) -> Dict[str, Any]:
    async with backoff_client() as client:
        channel_video_count = {}
        channel_search_ids = set()
        pages_to_fetch = 3
        next_page_token = page_token

        for page in range(pages_to_fetch):
            search_params = {
                "q": q,
                "part": "id,snippet",
                "type": "channel",
                "maxResults": 50,
                "key": settings.youtube_api_key,
            }

            if next_page_token:
                search_params["pageToken"] = next_page_token

            search_response = await client.get(f"{BASE}/search", params=search_params, timeout=20)
            search_response.raise_for_status()
            search_data = search_response.json()

            items = search_data.get("items", [])
            if not items:
                break

            for item in items:
                channel_id = item["id"]["channelId"]
                channel_search_ids.add(channel_id)
                channel_video_count[channel_id] = channel_video_count.get(channel_id, 0) + 5

            next_page_token = search_data.get("nextPageToken")
            if not next_page_token:
                break

        all_video_items = []
        next_page_token = None
        pages_to_fetch = 6

        for page in range(pages_to_fetch):
            search_params = {
                "q": q,
                "part": "id,snippet",
                "type": "video",
                "maxResults": 50,
                "key": settings.youtube_api_key,
                "order": "viewCount",
            }

            if next_page_token:
                search_params["pageToken"] = next_page_token

            search_response = await client.get(f"{BASE}/search", params=search_params, timeout=20)
            search_response.raise_for_status()
            search_data = search_response.json()

            items = search_data.get("items", [])
            if not items:
                break

            all_video_items.extend(items)

            next_page_token = search_data.get("nextPageToken")
            if not next_page_token:
                break

        for item in all_video_items:
            channel_id = item["snippet"]["channelId"]
            channel_video_count[channel_id] = channel_video_count.get(channel_id, 0) + 1

        all_candidate_ids = list(channel_video_count.keys())

        if not all_candidate_ids:
            return {"channels": [], "nextPageToken": None}

        all_channels = []
        batch_size = 50

        for i in range(0, len(all_candidate_ids), batch_size):
            batch_ids = all_candidate_ids[i:i + batch_size]
            channels_params = {
                "part": "snippet,statistics,contentDetails,topicDetails",  # Added topicDetails
                "id": ",".join(batch_ids),
                "key": settings.youtube_api_key,
            }

            channels_response = await client.get(f"{BASE}/channels", params=channels_params, timeout=20)
            channels_response.raise_for_status()
            channels_data = channels_response.json()
            all_channels.extend(channels_data.get("items", []))

        filtered_channels = []
        for channel in all_channels:
            channel_id = channel["id"]
            total_videos = int(channel["statistics"].get("videoCount", 0))
            related_videos = channel_video_count.get(channel_id, 0)

            topic_match = False
            topic_categories = channel.get("topicDetails", {}).get("topicCategories", [])
            if topic_categories:
                topics = []
                for url in topic_categories:
                    topic_name = url.split("/")[-1].replace("_", " ").lower()
                    topics.append(topic_name)

                query_lower = q.lower()
                for topic in topics:
                    if query_lower in topic or topic in query_lower:
                        topic_match = True
                        break

            is_direct_match = channel_id in channel_search_ids


            if is_direct_match:
                filtered_channels.append((channel_id, related_videos + 10, channel))  # Bonus score
            elif topic_match:
                if total_videos == 0:
                    continue
                elif total_videos < 1000:
                    if related_videos >= 2:  # Reduced from 3
                        filtered_channels.append((channel_id, related_videos + 5, channel))
                elif total_videos < 5000:
                    if related_videos >= 3:  # Reduced from 5
                        filtered_channels.append((channel_id, related_videos + 5, channel))
                else:
                    if related_videos >= 5:  # Reduced from 10
                        filtered_channels.append((channel_id, related_videos + 5, channel))
            elif total_videos == 0:
                continue
            elif total_videos < 1000:
                if related_videos >= 3:
                    filtered_channels.append((channel_id, related_videos, channel))
            elif total_videos < 5000:
                if related_videos >= 5:
                    filtered_channels.append((channel_id, related_videos, channel))
            else:
                ratio = related_videos / total_videos
                if related_videos >= 10 or (related_videos >= 5 and ratio >= 0.01):
                    filtered_channels.append((channel_id, related_videos, channel))

        filtered_channels.sort(key=lambda x: x[1], reverse=True)

        selected_channels = [ch for _, _, ch in filtered_channels[:max_results]]

        if not selected_channels:
            return {"channels": [], "nextPageToken": None}

        channels_with_playlists = []
        for channel in selected_channels:
            uploads_playlist_id = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
            channels_with_playlists.append((channel, uploads_playlist_id))

        async def get_none():
            return None

        latest_upload_tasks = [
            get_latest_upload_date(client, playlist_id) if playlist_id else get_none()
            for _, playlist_id in channels_with_playlists
        ]
        latest_upload_dates = await asyncio.gather(*latest_upload_tasks)

        results = []
        for (channel, _), latest_upload_date in zip(channels_with_playlists, latest_upload_dates):
            subscriber_count = int(channel["statistics"].get("subscriberCount", 0))
            video_count = int(channel["statistics"].get("videoCount", 0))
            view_count = int(channel["statistics"].get("viewCount", 0))

            topic_categories = channel.get("topicDetails", {}).get("topicCategories", [])
            topics = []
            if topic_categories:
                for url in topic_categories:
                    topic_name = url.split("/")[-1].replace("_", " ")
                    topics.append(topic_name)

            results.append({
                "channelId": channel["id"],
                "title": channel["snippet"]["title"],
                "description": channel["snippet"]["description"],
                "thumbnailUrl": channel["snippet"]["thumbnails"]["default"]["url"],
                "subscriberCount": subscriber_count,
                "videoCount": video_count,
                "viewCount": view_count,
                "customUrl": channel["snippet"].get("customUrl", ""),
                "country": channel["snippet"].get("country", ""),
                "publishedAt": channel["snippet"].get("publishedAt", ""),
                "latestUploadDate": latest_upload_date,
                "topics": topics,  # Added topic information
            })

        results.sort(key=lambda x: x["subscriberCount"], reverse=True)

        return {
            "channels": results,
            "nextPageToken": next_page_token
        }


async def search_channel_by_name(channel_name: str) -> Optional[str]:
    async with backoff_client() as client:
        search_params = {
            "part": "snippet",
            "q": channel_name,
            "type": "channel",
            "maxResults": 1,
            "key": settings.youtube_api_key,
        }

        try:
            response = await client.get(f"{BASE}/search", params=search_params, timeout=10)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if items:
                return items[0]["id"]["channelId"]
        except Exception:
            pass

        return None


async def get_channels_by_names(channel_names: List[str]) -> List[Dict[str, Any]]:
    channel_ids = []

    for name in channel_names:
        channel_id = await search_channel_by_name(name)
        if channel_id:
            channel_ids.append(channel_id)

    if not channel_ids:
        return []

    async with backoff_client() as client:
        all_channels_data = []
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
            all_channels_data.extend(channels_data.get("items", []))

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
