import httpx
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
import logging
import time

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
        
        # Add episode info for TV shows
        if media_type == "show" and season is not None and episode is not None:
            params["numberseason"] = season
            params["numberepisode"] = episode
        
        # Add quality filters
        if video_quality:
            params["videoquality"] = ",".join(video_quality)
        
        # Include additional useful parameters
        params["protocoltorent"] = 1  # Include torrents
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
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Orionoid API connection"""
        start_time = time.time()
        health_result = {
            "status": "unhealthy",
            "message": "Unknown error",
            "responseTime": None,
            "userInfo": None
        }
        
        try:
            # Check API connectivity and authentication by getting user info
            user_info = await self.get_user_info()
            response_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
            
            # Check if the response is successful
            if user_info.get("result", {}).get("status") == "success":
                user_data = user_info.get("data", {})
                health_result = {
                    "status": "healthy",
                    "message": "Connected to Orionoid API",
                    "responseTime": response_time,
                    "userInfo": {
                        "username": user_data.get("email", "Unknown"),
                        "premium": user_data.get("subscription", {}).get("package", {}).get("premium", False),
                        "apiCallsRemaining": user_data.get("requests", {}).get("streams", {}).get("daily", {}).get("remaining", 0)
                    }
                }
            else:
                error_msg = user_info.get("result", {}).get("message", "API returned error status")
                health_result = {
                    "status": "unhealthy",
                    "message": f"Orionoid API error: {error_msg}",
                    "responseTime": response_time,
                    "userInfo": None
                }
        
        except httpx.TimeoutException:
            health_result["message"] = "Connection timeout"
            health_result["responseTime"] = int((time.time() - start_time) * 1000)
        
        except httpx.HTTPStatusError as e:
            health_result["message"] = f"HTTP error {e.response.status_code}"
            health_result["responseTime"] = int((time.time() - start_time) * 1000)
            
            # Check for specific authentication errors
            if e.response.status_code in [401, 403]:
                health_result["message"] = "Authentication failed - invalid API keys"
        
        except httpx.ConnectError:
            health_result["message"] = "Cannot connect to Orionoid API"
            health_result["responseTime"] = int((time.time() - start_time) * 1000)
        
        except Exception as e:
            health_result["message"] = f"Unexpected error: {str(e)}"
            health_result["responseTime"] = int((time.time() - start_time) * 1000)
        
        return health_result