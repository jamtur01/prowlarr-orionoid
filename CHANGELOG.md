# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-02-27

### Fixed
- Health check drains API quota — cache TTL increased from 30s to `cache_ttl` (default 300s) and all responses (including unhealthy) are now cached, preventing runaway API calls when quota is exhausted
- Typo in Orionoid API parameter `protocoltorent` → `protocoltorrent` caused torrent results to be silently dropped
- Season-only TV searches ignored — season and episode parameters are now sent independently, enabling full-season pack searches from Prowlarr
- Dual movie+TV search ran sequentially — now uses `asyncio.gather()` for parallel execution
- `_status_code` internal field leaked in health check JSON response
- `tmdb_id` was not forwarded for TV searches
- Item build errors logged via `print()` instead of the configured logger

## [1.0.0] - 2025-01-30

### Added
- Initial release of Prowlarr-Orionoid Bridge
- Full Torznab/Newznab protocol support
- Search functionality for movies and TV shows
  - Search by query string
  - Search by IMDb ID, TVDB ID, and TMDB ID
  - Season and episode filtering for TV shows
- Comprehensive health check endpoint with detailed status reporting
- Docker containerization with health checks
- Configuration management via environment variables
- Optional API key authentication for Prowlarr
- Detailed logging with configurable levels
- Support for both torrent and NZB results from Orionoid
- Automatic quality categorization (SD/HD/UHD)
- Combined movie and TV search when no category is specified
- Intelligent TV show detection based on API data and file naming
- Graceful error handling for partial search failures

### Technical Details
- Built with FastAPI for high performance async operations
- Uses httpx for async HTTP requests to Orionoid API
- XML generation via lxml for Torznab/Newznab responses
- Pydantic for configuration and data validation
- Full type hints throughout the codebase
- Production-ready Docker setup with non-root user
- Multi-architecture Docker support (amd64, arm64, arm/v7)
- GitHub Actions for CI/CD with automatic Docker Hub publishing

### Configuration
- App API key is now hardcoded as per Orionoid documentation
- Only user API key needs to be configured via environment variable

[1.1.0]: https://github.com/jamtur01/prowlarr-orionoid/releases/tag/v1.1.0
[1.0.0]: https://github.com/jamtur01/prowlarr-orionoid/releases/tag/v1.0.0