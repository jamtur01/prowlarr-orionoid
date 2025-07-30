from fastapi import FastAPI, Query, Response, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from typing import Optional, Dict, Any
import logging
import uvicorn
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import time
import asyncio

from config import settings
from orionoid_client import OrionoidClient
from torznab_builder import TorznabBuilder
from __version__ import __version__

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global client instance and metrics
orion_client: Optional[OrionoidClient] = None
startup_time: Optional[float] = None
last_successful_search: Optional[datetime] = None
health_check_cache: Optional[Dict[str, Any]] = None
health_check_cache_time: Optional[float] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global orion_client, startup_time
    orion_client = OrionoidClient(settings.orionoid_app_api_key, settings.orionoid_user_api_key)
    startup_time = time.time()
    logger.info("Orionoid client initialized")
    
    # Test connection
    try:
        await orion_client.__aenter__()
        user_info = await orion_client.get_user_info()
        
        # Check if we got a successful response
        if user_info.get("result", {}).get("status") == "success":
            user_data = user_info.get("data", {})
            username = user_data.get("email", "Unknown")
            is_premium = user_data.get("subscription", {}).get("package", {}).get("premium", False)
            remaining_requests = user_data.get("requests", {}).get("streams", {}).get("daily", {}).get("remaining", 0)
            logger.info(f"Connected to Orionoid. User: {username}, Premium: {is_premium}, Daily requests remaining: {remaining_requests:,}")
        else:
            # API returned an error
            error_msg = user_info.get("result", {}).get("message", "Unknown error")
            logger.warning(f"Orionoid API returned error: {error_msg}")
            logger.info("Service started but Orionoid authentication may need attention")
    except Exception as e:
        logger.error(f"Failed to connect to Orionoid: {e}")
    
    yield
    
    # Shutdown
    if orion_client:
        await orion_client.__aexit__(None, None, None)
    logger.info("Orionoid client closed")


app = FastAPI(
    title="Prowlarr-Orionoid Bridge",
    description="A Torznab/Newznab compatible indexer for Orionoid",
    version=__version__,
    lifespan=lifespan
)


def check_api_key(apikey: Optional[str] = None):
    """Check if API key is valid (if configured)"""
    if settings.prowlarr_api_key and apikey != settings.prowlarr_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "title": "Prowlarr-Orionoid Bridge",
        "version": __version__,
        "endpoints": {
            "capabilities": "/api?t=caps",
            "search": "/api?t=search&q=query",
            "tv-search": "/api?t=tvsearch&q=query&season=1&ep=1",
            "movie-search": "/api?t=movie&q=query",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check(force: bool = Query(False, description="Force fresh check, bypassing cache")):
    """Health check endpoint for monitoring service health"""
    global health_check_cache, health_check_cache_time
    
    # Check cache unless forced
    if not force and health_check_cache and health_check_cache_time:
        if (time.time() - health_check_cache_time) < 30:  # 30 second cache
            return JSONResponse(
                content=health_check_cache,
                status_code=health_check_cache["_status_code"]
            )
    
    start_time = time.time()
    checks = {}
    
    # Check if client is initialized
    dependencies_status = "healthy" if orion_client else "unhealthy"
    dependencies_message = "All dependencies operational" if orion_client else "Orionoid client not initialized"
    
    # Initialize default response structure
    overall_status = "healthy"
    
    # Perform Orionoid API health check
    orionoid_check = {
        "status": "unhealthy",
        "message": "Not checked",
        "responseTime": None,
        "lastChecked": datetime.now(timezone.utc).isoformat()
    }
    
    auth_check = {
        "status": "unhealthy", 
        "message": "Not checked",
        "userInfo": None
    }
    
    if orion_client:
        try:
            # Run health check on Orionoid client
            health_result = await orion_client.health_check()
            
            # Update Orionoid API check
            orionoid_check["status"] = health_result["status"]
            orionoid_check["message"] = health_result["message"]
            orionoid_check["responseTime"] = health_result["responseTime"]
            
            # Update authentication check
            if health_result["status"] == "healthy":
                auth_check["status"] = "healthy"
                auth_check["message"] = "API keys are valid"
                auth_check["userInfo"] = health_result["userInfo"]
            else:
                auth_check["status"] = "unhealthy"
                auth_check["message"] = health_result["message"]
                overall_status = "unhealthy"
                
        except Exception as e:
            logger.error(f"Health check error: {e}")
            orionoid_check["status"] = "unhealthy"
            orionoid_check["message"] = f"Health check failed: {str(e)}"
            auth_check["status"] = "unhealthy"
            auth_check["message"] = "Unable to verify authentication"
            overall_status = "unhealthy"
    else:
        orionoid_check["status"] = "unhealthy"
        orionoid_check["message"] = "Orionoid client not initialized"
        auth_check["status"] = "unhealthy"
        auth_check["message"] = "Cannot check authentication - client not initialized"
        overall_status = "unhealthy"
    
    # Check search capability
    search_check = {
        "status": "healthy" if last_successful_search else "degraded",
        "message": "Search functionality operational" if last_successful_search else "No searches performed yet",
        "lastSuccessfulSearch": last_successful_search.isoformat() if last_successful_search else None
    }
    
    # If we haven't had a successful search in 5 minutes, mark as degraded
    if last_successful_search:
        time_since_search = (datetime.now(timezone.utc) - last_successful_search).total_seconds()
        if time_since_search > 300:  # 5 minutes
            search_check["status"] = "degraded"
            search_check["message"] = f"No searches in {int(time_since_search / 60)} minutes"
    
    # Compile all checks
    checks = {
        "orionoid_api": orionoid_check,
        "authentication": auth_check,
        "search_capability": search_check,
        "dependencies": {
            "status": dependencies_status,
            "httpClient": "connected" if orion_client else "not initialized",
            "xmlBuilder": "operational"  # Always operational as it's stateless
        }
    }
    
    # Determine overall status based on component statuses
    if any(check.get("status") == "unhealthy" for check in checks.values()):
        overall_status = "unhealthy"
    elif any(check.get("status") == "degraded" for check in checks.values()):
        overall_status = "degraded"
    
    # Calculate uptime
    uptime = int(time.time() - startup_time) if startup_time else 0
    
    # Build response
    response = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": __version__,
        "checks": checks,
        "uptime": uptime,
        "environment": {
            "host": settings.service_host,
            "port": settings.service_port,
            "logLevel": settings.log_level
        }
    }
    
    # Determine status code
    status_code = 503 if overall_status == "unhealthy" else 200
    response["_status_code"] = status_code
    
    # Cache successful responses
    if overall_status != "unhealthy":
        health_check_cache = response.copy()
        health_check_cache_time = time.time()
    
    return JSONResponse(content=response, status_code=status_code)


@app.get("/api", response_class=PlainTextResponse)
async def api_endpoint(
    t: str = Query(..., description="API function type"),
    apikey: Optional[str] = Query(None, description="API key for authentication"),
    q: Optional[str] = Query(None, description="Search query"),
    cat: Optional[str] = Query(None, description="Category"),
    imdbid: Optional[str] = Query(None, description="IMDb ID"),
    tvdbid: Optional[str] = Query(None, description="TVDB ID"),
    tmdbid: Optional[str] = Query(None, description="TMDB ID"),
    season: Optional[int] = Query(None, description="Season number"),
    ep: Optional[int] = Query(None, description="Episode number"),
    limit: Optional[int] = Query(100, description="Result limit"),
    offset: Optional[int] = Query(0, description="Result offset"),
    extended: Optional[int] = Query(None, description="Extended attributes")
):
    """Main API endpoint for Torznab/Newznab protocol"""
    
    # Log incoming request parameters for debugging
    logger.info(f"API request: t={t}, q={q}, cat={cat}, imdbid={imdbid}, tvdbid={tvdbid}, tmdbid={tmdbid}, season={season}, ep={ep}, limit={limit}")
    
    try:
        # Handle capabilities request (no auth required)
        if t == "caps":
            return Response(
                content=TorznabBuilder.build_capabilities(),
                media_type="application/xml"
            )
        
        # Check API key for other requests
        check_api_key(apikey)
        
        # Ensure we have a client
        if not orion_client:
            raise HTTPException(status_code=503, detail="Orionoid client not initialized")
        
        # Limit max results
        limit = min(limit or settings.default_search_limit, settings.max_search_limit)
        
        # Handle different search types
        if t == "search":
            # General search - determine media type from categories
            if cat:
                # Check if categories are TV categories (5xxx)
                categories = [int(c) for c in cat.split(",") if c.isdigit()]
                if any(c >= 5000 and c < 6000 for c in categories):
                    media_type = "show"
                else:
                    media_type = "movie"
                
                results = await search_orionoid(
                    query=q,
                    imdb_id=imdbid,
                    media_type=media_type,
                    limit=limit
                )
            else:
                # No category specified - search both movies and TV shows
                logger.info("No category specified - searching both movies and TV shows")
                
                # Search movies
                try:
                    movie_results = await search_orionoid(
                        query=q,
                        imdb_id=imdbid,
                        media_type="movie",
                        limit=limit // 2  # Split limit between movie and TV
                    )
                except Exception as e:
                    logger.warning(f"Movie search failed: {e}")
                    movie_results = None
                
                # Search TV shows
                try:
                    tv_results = await search_orionoid(
                        query=q,
                        imdb_id=imdbid,
                        media_type="show",
                        limit=limit // 2
                    )
                except Exception as e:
                    logger.warning(f"TV search failed: {e}")
                    tv_results = None
                
                # Combine results
                results = {
                    "result": {"status": "success"},
                    "data": {
                        "streams": [],
                        "count": 0
                    }
                }
                
                # Add movie streams (mark them as movies)
                if movie_results and movie_results.get("result", {}).get("status") == "success":
                    movie_streams = movie_results.get("data", {}).get("streams", [])
                    for stream in movie_streams:
                        stream["_media_type"] = "movie"
                    results["data"]["streams"].extend(movie_streams)
                
                # Add TV streams (mark them as shows)
                if tv_results and tv_results.get("result", {}).get("status") == "success":
                    tv_streams = tv_results.get("data", {}).get("streams", [])
                    for stream in tv_streams:
                        stream["_media_type"] = "show"
                    results["data"]["streams"].extend(tv_streams)
                
                # If both searches failed, return an error
                if movie_results is None and tv_results is None:
                    raise Exception("Both movie and TV searches failed")
                
                results["data"]["count"] = len(results["data"]["streams"])
        
        elif t == "tvsearch":
            # TV search
            results = await search_orionoid(
                query=q,
                imdb_id=imdbid,
                tvdb_id=tvdbid,
                media_type="show",
                season=season,
                episode=ep,
                limit=limit
            )
        
        elif t == "movie":
            # Movie search
            results = await search_orionoid(
                query=q,
                imdb_id=imdbid,
                tmdb_id=tmdbid,
                media_type="movie",
                limit=limit
            )
        
        else:
            return Response(
                content=TorznabBuilder.build_error(201, f"Incorrect parameter: unknown function '{t}'"),
                media_type="application/xml"
            )
        
        # Build and return XML response
        return Response(
            content=TorznabBuilder.build_search_results(results, t),
            media_type="application/xml"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return Response(
            content=TorznabBuilder.build_error(100, str(e)),
            media_type="application/xml"
        )


async def search_orionoid(
    query: Optional[str] = None,
    imdb_id: Optional[str] = None,
    tvdb_id: Optional[str] = None,
    tmdb_id: Optional[str] = None,
    media_type: str = "movie",
    season: Optional[int] = None,
    episode: Optional[int] = None,
    limit: int = 100
) -> dict:
    """Search Orionoid and return results"""
    global last_successful_search
    
    # Check if we have any search criteria
    if not any([query, imdb_id, tvdb_id, tmdb_id]):
        # For empty searches (Prowlarr connection test), do a real search for a popular movie
        logger.info("Empty search request - performing test search for 'The Matrix' to validate connection")
        query = "The Matrix"
        limit = 1  # Only need one result for validation
    
    # Clean up IDs (remove 'tt' prefix from IMDb IDs if present)
    if imdb_id and imdb_id.startswith("tt"):
        imdb_id = imdb_id[2:]
    
    # Perform search
    logger.info(f"Searching Orionoid with: query={query}, imdb_id={imdb_id}, tvdb_id={tvdb_id}, tmdb_id={tmdb_id}, media_type={media_type}, season={season}, episode={episode}")
    
    results = await orion_client.search_streams(
        query=query,
        imdb_id=imdb_id,
        tvdb_id=tvdb_id,
        tmdb_id=tmdb_id,
        media_type=media_type,
        season=season,
        episode=episode,
        limit=limit
    )
    
    # Check for errors
    if results.get("result", {}).get("status") != "success":
        error_msg = results.get("result", {}).get("message", "Unknown error")
        raise Exception(f"Orionoid API error: {error_msg}")
    
    # Log results
    streams_count = len(results.get("data", {}).get("streams", []))
    logger.info(f"Orionoid returned {streams_count} streams")
    
    # Update last successful search time
    last_successful_search = datetime.now(timezone.utc)
    
    return results


# Additional Prowlarr-specific endpoints
@app.get("/{indexer_id}/api", response_class=PlainTextResponse)
async def api_endpoint_with_id(
    indexer_id: str,
    t: str = Query(...),
    apikey: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    cat: Optional[str] = Query(None),
    imdbid: Optional[str] = Query(None),
    tvdbid: Optional[str] = Query(None),
    tmdbid: Optional[str] = Query(None),
    season: Optional[int] = Query(None),
    ep: Optional[int] = Query(None),
    limit: Optional[int] = Query(100),
    offset: Optional[int] = Query(0),
    extended: Optional[int] = Query(None)
):
    """Alternative API endpoint with indexer ID in path (Prowlarr compatibility)"""
    return await api_endpoint(t, apikey, q, cat, imdbid, tvdbid, tmdbid, season, ep, limit, offset, extended)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=False
    )