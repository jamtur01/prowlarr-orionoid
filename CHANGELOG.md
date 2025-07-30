# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-29

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

### Technical Details
- Built with FastAPI for high performance async operations
- Uses httpx for async HTTP requests to Orionoid API
- XML generation via lxml for Torznab/Newznab responses
- Pydantic for configuration and data validation
- Full type hints throughout the codebase
- Production-ready Docker setup with non-root user

### Configuration
- Environment variables renamed for clarity:
  - `ORIONOID_APP_API_KEY` (formerly `ORIONOID_APP_KEY`)
  - `ORIONOID_USER_API_KEY` (formerly `ORIONOID_USER_KEY`)

[1.0.0]: https://github.com/jamtur01/prowlarr-orionoid/releases/tag/v1.0.0