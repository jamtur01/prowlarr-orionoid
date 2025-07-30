from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Orionoid API credentials
    # App key is hardcoded as per Orionoid documentation
    # This is the official Prowlarr-Orionoid app key
    orionoid_app_api_key: str = "WYC8JEBTCABDCB6SDNNGMJHP8AVSBEHV"
    orionoid_user_api_key: str
    
    # Service configuration
    service_port: int = 8080
    service_host: str = "0.0.0.0"
    
    # Torznab/Newznab configuration
    indexer_name: str = "Orionoid"
    indexer_description: str = "Orionoid Torznab Indexer"
    
    # API key for Prowlarr authentication (optional)
    # If set, Prowlarr must provide this key as 'apikey' parameter
    prowlarr_api_key: Optional[str] = None
    
    # Default search limits
    default_search_limit: int = 100
    max_search_limit: int = 1000
    
    # Logging
    log_level: str = "INFO"
    
    # Cache settings (in seconds)
    cache_ttl: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()