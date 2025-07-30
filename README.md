# Prowlarr-Orionoid Bridge

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/jamtur01/prowlarr-orionoid/releases)
[![CI Build](https://github.com/jamtur01/prowlarr-orionoid/actions/workflows/ci.yml/badge.svg)](https://github.com/jamtur01/prowlarr-orionoid/actions/workflows/ci.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/jamtur01/prowlarr-orionoid)](https://hub.docker.com/r/jamtur01/prowlarr-orionoid)
[![Docker Image Size](https://img.shields.io/docker/image-size/jamtur01/prowlarr-orionoid/latest)](https://hub.docker.com/r/jamtur01/prowlarr-orionoid)

A Torznab/Newznab compatible indexer service that allows [Prowlarr](https://prowlarr.com/) to use [Orionoid](https://orionoid.com/) as an indexer. This service translates between Prowlarr's indexer protocol and Orionoid's API, enabling seamless integration.

## Features

- Full Torznab/Newznab protocol support
- Search by query, IMDb ID, TVDB ID, and TMDB ID
- Support for movies and TV shows
- Configurable search limits
- Docker containerization
- Comprehensive health check endpoint with detailed status reporting
- Optional API key authentication
- Multi-architecture support (amd64, arm64, arm/v7)

## Quick Start

### Using Docker (Recommended)

```bash
docker run -d \
  --name prowlarr-orionoid \
  -p 8080:8080 \
  -e ORIONOID_APP_API_KEY=your_app_api_key \
  -e ORIONOID_USER_API_KEY=your_user_api_key \
  jamtur01/prowlarr-orionoid:latest
```

### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
services:
  prowlarr-orionoid:
    image: jamtur01/prowlarr-orionoid:latest
    container_name: prowlarr-orionoid
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - ORIONOID_APP_API_KEY=your_app_api_key
      - ORIONOID_USER_API_KEY=your_user_api_key
```

Then run:
```bash
docker-compose up -d
```

## Prerequisites

1. **Orionoid Account**: You need an active Orionoid account with API access
2. **Orionoid API Keys**: 
   - **App API Key**: Register your app at [Orionoid](https://orionoid.com) to get an app API key
   - **User API Key**: Get from your Orionoid account settings

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ORIONOID_APP_API_KEY` | Yes | - | Your Orionoid app API key |
| `ORIONOID_USER_API_KEY` | Yes | - | Your Orionoid user API key |
| `SERVICE_PORT` | No | 8080 | Port to run the service on |
| `SERVICE_HOST` | No | 0.0.0.0 | Host to bind the service to |
| `PROWLARR_API_KEY` | No | - | Optional API key for Prowlarr authentication |
| `DEFAULT_SEARCH_LIMIT` | No | 100 | Default number of results to return |
| `MAX_SEARCH_LIMIT` | No | 1000 | Maximum allowed search results |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Adding to Prowlarr

1. In Prowlarr, go to **Settings** → **Indexers**

2. Click the **+** button to add a new indexer

3. Select **Torznab** → **Custom Torznab**

4. Configure the indexer:
   - **Name**: Orionoid
   - **Enable RSS**: Yes (if desired)
   - **Enable Automatic Search**: Yes
   - **Enable Interactive Search**: Yes
   - **URL**: `http://localhost:8080` (or your Docker host IP)
   - **API Path**: `/api`
   - **API Key**: Leave blank unless you set `PROWLARR_API_KEY`
   - **Categories**: Select desired categories (Movies, TV, etc.)

5. Click **Test** to verify the connection

6. Save the indexer

## Supported Architectures

This image supports multiple architectures:
- `linux/amd64` - Standard x86-64
- `linux/arm64` - ARM 64-bit (Raspberry Pi 4, Apple Silicon)
- `linux/arm/v7` - ARM 32-bit (Raspberry Pi 2/3)

## API Endpoints

### Health Check
```
GET /health
GET /health?force=true
```
Returns detailed health status including Orionoid connectivity, authentication status, and service uptime.

### Capabilities
```
GET /api?t=caps
```
Returns the indexer capabilities (supported search types, categories, etc.)

### Search
```
GET /api?t=search&q=query
```
General search across all categories

### TV Search
```
GET /api?t=tvsearch&q=query&season=1&ep=1
GET /api?t=tvsearch&tvdbid=12345&season=1&ep=1
```
Search for TV shows with optional season/episode filtering

### Movie Search
```
GET /api?t=movie&q=query
GET /api?t=movie&imdbid=tt1234567
```
Search for movies

## Building from Source

### Using Docker

```bash
git clone https://github.com/jamtur01/prowlarr-orionoid.git
cd prowlarr-orionoid
docker build -t prowlarr-orionoid .
docker run -d \
  --name prowlarr-orionoid \
  -p 8080:8080 \
  -e ORIONOID_APP_API_KEY=your_app_api_key \
  -e ORIONOID_USER_API_KEY=your_user_api_key \
  prowlarr-orionoid
```

### Running Locally

1. Install Python 3.11 or higher

2. Clone the repository:
   ```bash
   git clone https://github.com/jamtur01/prowlarr-orionoid.git
   cd prowlarr-orionoid
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file:
   ```env
   ORIONOID_APP_API_KEY=your_app_api_key
   ORIONOID_USER_API_KEY=your_user_api_key
   ```

5. Run the service:
   ```bash
   python main.py
   ```

## Troubleshooting

### Service won't start
- Check that your Orionoid API keys are correct
- Verify the port isn't already in use
- Check Docker logs: `docker logs prowlarr-orionoid`

### No results returned
- Verify your Orionoid account has API access
- Check that you haven't exceeded your daily API limits
- Try searching with different queries or IDs

### Prowlarr connection test fails
- Ensure the service is running and accessible
- Check the URL and port are correct
- Verify any API key is correctly configured

### Health check failing
- Check `/health` endpoint for detailed error information
- Verify Orionoid API keys are valid
- Ensure network connectivity to Orionoid API

## Development

### Project Structure
```
prowlarr-orionoid/
├── main.py              # FastAPI application
├── orionoid_client.py   # Orionoid API client
├── torznab_builder.py   # Torznab XML response builder
├── config.py            # Configuration management
├── __version__.py       # Version information
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker container definition
├── docker-compose.yml  # Docker Compose configuration
├── CHANGELOG.md        # Version history
└── README.md          # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Links

- [GitHub Repository](https://github.com/jamtur01/prowlarr-orionoid)
- [Docker Hub](https://hub.docker.com/r/jamtur01/prowlarr-orionoid)
- [Issues & Support](https://github.com/jamtur01/prowlarr-orionoid/issues)
- [Changelog](https://github.com/jamtur01/prowlarr-orionoid/blob/main/CHANGELOG.md)

## License

This project is provided as-is for educational and personal use. Please respect Orionoid's terms of service and API usage limits.