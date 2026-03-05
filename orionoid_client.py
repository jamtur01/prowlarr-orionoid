import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)


class OrionoidClient:
    def __init__(self, app_key: str, user_key: str):
        self.app_key = app_key
        self.user_key = user_key
        self.base_url = "https://api.orionoid.com"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to Orionoid API"""
        params.update({
            "keyapp": self.app_key,
            "keyuser": self.user_key
        })

        try:
            response = await self.client.post(
                self.base_url,
                data=urlencode(params),
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"Error making request to Orionoid: {e}")
            raise

    async def search_streams(
        self,
        query: Optional[str] = None,
        imdb_id: Optional[str] = None,
        tvdb_id: Optional[str] = None,
        tmdb_id: Optional[str] = None,
        media_type: str = "movie",
        season: Optional[int] = None,
        episode: Optional[int] = None,
        limit: int = 100,
        video_quality: Optional[List[str]] = None,
        sort: str = "best"
    ) -> Dict[str, Any]:
        """Search for streams on Orionoid"""
        params = {
            "mode": "stream",
            "action": "retrieve",
            "type": media_type,
            "limitcount": limit,
            "sort": sort
        }

        # Add search criteria
        if query:
            params["query"] = query
        if imdb_id:
            params["idimdb"] = imdb_id
        if tvdb_id:
            params["idtvdb"] = tvdb_id
        if tmdb_id:
            params["idtmdb"] = tmdb_id

        # Add season/episode info for TV shows
        if media_type == "show":
            if season is not None:
                params["numberseason"] = season
            if episode is not None:
                params["numberepisode"] = episode

        # Add quality filters
        if video_quality:
            params["videoquality"] = ",".join(video_quality)

        # Include additional useful parameters
        params["protocoltorrent"] = 1  # Include torrents
        params["protocolnzb"] = 1      # Include NZBs
        params["debridlookup"] = 0     # Skip debrid lookup to save API calls

        return await self._make_request(params)

    async def get_user_info(self) -> Dict[str, Any]:
        """Get user account information"""
        params = {
            "mode": "user",
            "action": "retrieve"
        }
        return await self._make_request(params)

    async def get_app_info(self) -> Dict[str, Any]:
        """Get app information"""
        params = {
            "mode": "app",
            "action": "retrieve"
        }
        return await self._make_request(params)

