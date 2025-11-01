
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
    """
    Get the latest upload date from a channel's uploads playlist
    """
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
        # If we can't get the latest upload, just return None
        pass
    return None


async def search_channels(q: str, max_results: int = 150, page_token: str = None) -> Dict[str, Any]:
    """
    Hybrid search: Combines channel search + video-based channel discovery
    1. Direct channel search (finds channels with keyword in name/description)
    2. Video search -> extract channels (finds channels making content about the keyword)
    3. Count how many videos each channel has with the keyword
    4. Merge and deduplicate results
    """
    async with backoff_client() as client:
        channel_video_count = {}  # Track how many videos each channel has

        # Step 1: Direct CHANNEL search (good for channels with keyword in name)
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
                # Channels found via direct search get bonus points
                channel_video_count[channel_id] = channel_video_count.get(channel_id, 0) + 5

            next_page_token = search_data.get("nextPageToken")
            if not next_page_token:
                break

        # Step 2: VIDEO search -> extract channels (finds channels making content)
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

        # Count videos per channel
        for item in all_video_items:
            channel_id = item["snippet"]["channelId"]
            channel_video_count[channel_id] = channel_video_count.get(channel_id, 0) + 1

        # Step 3: Get all candidate channel IDs (for filtering later)
        all_candidate_ids = list(channel_video_count.keys())

        if not all_candidate_ids:
            return {"channels": [], "nextPageToken": None}

        # Step 4: Get detailed channel information in batches (max 50 IDs per request)
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

        # Step 4.5: Filter channels based on relevance ratio + topic matching
        filtered_channels = []
        for channel in all_channels:
            channel_id = channel["id"]
            total_videos = int(channel["statistics"].get("videoCount", 0))
            related_videos = channel_video_count.get(channel_id, 0)

            # Check if channel's topics match the search keyword
            topic_match = False
            topic_categories = channel.get("topicDetails", {}).get("topicCategories", [])
            if topic_categories:
                # Extract topic names from Wikipedia URLs
                # e.g., "https://en.wikipedia.org/wiki/Camping" -> "Camping"
                topics = []
                for url in topic_categories:
                    topic_name = url.split("/")[-1].replace("_", " ").lower()
                    topics.append(topic_name)

                # Check if search query matches any topic
                query_lower = q.lower()
                for topic in topics:
                    if query_lower in topic or topic in query_lower:
                        topic_match = True
                        break

            # Calculate relevance score
            is_direct_match = channel_id in channel_search_ids

            # Filter criteria with topic boost:
            # 1. Direct channel search match (always included)
            # 2. Topic match (gives bonus, reduces video count requirement)
            # 3. Video count based on channel size

            if is_direct_match:
                # Channels found via direct search always included
                filtered_channels.append((channel_id, related_videos + 10, channel))  # Bonus score
            elif topic_match:
                # Topic match: reduce requirements by 1-2 videos
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
                # Small/medium channels: need at least 3 related videos
                if related_videos >= 3:
                    filtered_channels.append((channel_id, related_videos, channel))
            elif total_videos < 5000:
                # Larger channels: need at least 5 related videos
                if related_videos >= 5:
                    filtered_channels.append((channel_id, related_videos, channel))
            else:
                # Very large channels (news, etc): need at least 10 related videos OR 1% ratio
                ratio = related_videos / total_videos
                if related_videos >= 10 or (related_videos >= 5 and ratio >= 0.01):
                    filtered_channels.append((channel_id, related_videos, channel))

        # Sort by related video count (relevance)
        filtered_channels.sort(key=lambda x: x[1], reverse=True)

        # Take top channels and prepare for next steps
        selected_channels = [ch for _, _, ch in filtered_channels[:max_results]]

        if not selected_channels:
            return {"channels": [], "nextPageToken": None}

        # Step 5: Get latest upload date for each channel in parallel
        channels_with_playlists = []
        for channel in selected_channels:
            uploads_playlist_id = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
            channels_with_playlists.append((channel, uploads_playlist_id))

        # Fetch all latest upload dates in parallel
        async def get_none():
            return None

        latest_upload_tasks = [
            get_latest_upload_date(client, playlist_id) if playlist_id else get_none()
            for _, playlist_id in channels_with_playlists
        ]
        latest_upload_dates = await asyncio.gather(*latest_upload_tasks)

        # Step 6: Build results
        results = []
        for (channel, _), latest_upload_date in zip(channels_with_playlists, latest_upload_dates):
            subscriber_count = int(channel["statistics"].get("subscriberCount", 0))
            video_count = int(channel["statistics"].get("videoCount", 0))
            view_count = int(channel["statistics"].get("viewCount", 0))

            # Extract topic names from URLs
            topic_categories = channel.get("topicDetails", {}).get("topicCategories", [])
            topics = []
            if topic_categories:
                for url in topic_categories:
                    # Extract readable name from Wikipedia URL
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

        # Sort by subscriber count (descending)
        results.sort(key=lambda x: x["subscriberCount"], reverse=True)

        return {
            "channels": results,
            "nextPageToken": next_page_token
        }
