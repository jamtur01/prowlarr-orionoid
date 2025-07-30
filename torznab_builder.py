from lxml import etree
from datetime import datetime
from typing import List, Dict, Any, Optional
import re


class TorznabBuilder:
    """Build Torznab/Newznab compatible XML responses"""
    
    # Torznab category mappings
    CATEGORY_MOVIE = 2000
    CATEGORY_MOVIE_SD = 2030
    CATEGORY_MOVIE_HD = 2040
    CATEGORY_MOVIE_UHD = 2060
    CATEGORY_TV = 5000
    CATEGORY_TV_SD = 5030
    CATEGORY_TV_HD = 5040
    CATEGORY_TV_UHD = 5080
    
    @staticmethod
    def build_capabilities() -> str:
        """Build capabilities XML response"""
        root = etree.Element("caps")
        
        # Server info
        server = etree.SubElement(root, "server")
        server.set("version", "1.0")
        server.set("title", "Orionoid Torznab")
        server.set("strapline", "Orionoid Torznab Indexer")
        server.set("email", "")
        server.set("url", "https://orionoid.com")
        
        # Limits
        limits = etree.SubElement(root, "limits")
        limits.set("max", "100")
        limits.set("default", "100")
        
        # Registration
        registration = etree.SubElement(root, "registration")
        registration.set("available", "yes")
        registration.set("open", "yes")
        
        # Searching
        searching = etree.SubElement(root, "searching")
        search = etree.SubElement(searching, "search")
        search.set("available", "yes")
        search.set("supportedParams", "q,imdbid")
        
        tv_search = etree.SubElement(searching, "tv-search")
        tv_search.set("available", "yes")
        tv_search.set("supportedParams", "q,imdbid,tvdbid,season,ep")
        
        movie_search = etree.SubElement(searching, "movie-search")
        movie_search.set("available", "yes")
        movie_search.set("supportedParams", "q,imdbid,tmdbid")
        
        # Categories
        categories = etree.SubElement(root, "categories")
        
        # Movie categories
        cat_movie = etree.SubElement(categories, "category")
        cat_movie.set("id", str(TorznabBuilder.CATEGORY_MOVIE))
        cat_movie.set("name", "Movies")
        
        cat_movie_sd = etree.SubElement(cat_movie, "subcat")
        cat_movie_sd.set("id", str(TorznabBuilder.CATEGORY_MOVIE_SD))
        cat_movie_sd.set("name", "Movies/SD")
        
        cat_movie_hd = etree.SubElement(cat_movie, "subcat")
        cat_movie_hd.set("id", str(TorznabBuilder.CATEGORY_MOVIE_HD))
        cat_movie_hd.set("name", "Movies/HD")
        
        cat_movie_uhd = etree.SubElement(cat_movie, "subcat")
        cat_movie_uhd.set("id", str(TorznabBuilder.CATEGORY_MOVIE_UHD))
        cat_movie_uhd.set("name", "Movies/UHD")
        
        # TV categories
        cat_tv = etree.SubElement(categories, "category")
        cat_tv.set("id", str(TorznabBuilder.CATEGORY_TV))
        cat_tv.set("name", "TV")
        
        cat_tv_sd = etree.SubElement(cat_tv, "subcat")
        cat_tv_sd.set("id", str(TorznabBuilder.CATEGORY_TV_SD))
        cat_tv_sd.set("name", "TV/SD")
        
        cat_tv_hd = etree.SubElement(cat_tv, "subcat")
        cat_tv_hd.set("id", str(TorznabBuilder.CATEGORY_TV_HD))
        cat_tv_hd.set("name", "TV/HD")
        
        cat_tv_uhd = etree.SubElement(cat_tv, "subcat")
        cat_tv_uhd.set("id", str(TorznabBuilder.CATEGORY_TV_UHD))
        cat_tv_uhd.set("name", "TV/UHD")
        
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8').decode('utf-8')
    
    @staticmethod
    def build_search_results(orion_results: Dict[str, Any], query_type: str = "search") -> str:
        """Build search results RSS XML response"""
        # Create root with namespaces
        nsmap = {
            'newznab': 'http://www.newznab.com/DTD/2010/feeds/attributes/',
            'torznab': 'http://torznab.com/schemas/2015/feed'
        }
        root = etree.Element("rss", version="2.0", nsmap=nsmap)
        
        channel = etree.SubElement(root, "channel")
        
        # Channel metadata
        etree.SubElement(channel, "title").text = "Orionoid Torznab"
        etree.SubElement(channel, "description").text = "Orionoid Torznab Feed"
        etree.SubElement(channel, "link").text = "https://orionoid.com"
        
        # Response metadata
        response = etree.SubElement(channel, "{http://www.newznab.com/DTD/2010/feeds/attributes/}response")
        response.set("offset", "0")
        response.set("total", str(len(orion_results.get("data", {}).get("streams", []))))
        
        # Process each stream result
        streams = orion_results.get("data", {}).get("streams", [])
        for stream in streams:
            item = TorznabBuilder._build_item(stream, query_type)
            if item is not None:
                channel.append(item)
        
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8').decode('utf-8')
    
    @staticmethod
    def _build_item(stream: Dict[str, Any], query_type: str) -> Optional[etree.Element]:
        """Build individual item element"""
        try:
            item = etree.Element("item")
            
            # Basic metadata
            file_info = stream.get("file", {})
            video_info = stream.get("video", {})
            audio_info = stream.get("audio", {})
            meta_info = stream.get("meta", {})
            
            # Title construction
            title_parts = []
            if file_info.get("name"):
                title_parts.append(file_info["name"])
            elif meta_info.get("title"):
                title_parts.append(meta_info["title"])
            
            # Add quality info
            quality = video_info.get("quality", "").upper()
            if quality:
                title_parts.append(f"[{quality}]")
            
            # Add codec info
            codec = video_info.get("codec", "").upper()
            if codec:
                title_parts.append(f"[{codec}]")
            
            title = " ".join(title_parts) if title_parts else "Unknown"
            etree.SubElement(item, "title").text = title
            
            # GUID
            guid = stream.get("id", "")
            guid_elem = etree.SubElement(item, "guid")
            guid_elem.text = guid
            guid_elem.set("isPermaLink", "false")
            
            # Link (magnet or direct link)
            links = stream.get("links", [])
            if links:
                etree.SubElement(item, "link").text = links[0]
            
            # Comments (Orionoid page)
            etree.SubElement(item, "comments").text = "https://orionoid.com"
            
            # Published date
            time_info = stream.get("time", {})
            if time_info and time_info.get("added"):
                pub_date = datetime.fromtimestamp(time_info["added"])
                etree.SubElement(item, "pubDate").text = pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000")
            
            # Size
            size = file_info.get("size", 0)
            etree.SubElement(item, "size").text = str(size) if size else "0"
            
            # Enclosure (for torrent/nzb download)
            if links:
                enclosure = etree.SubElement(item, "enclosure")
                enclosure.set("url", links[0])
                enclosure.set("length", str(size) if size else "0")
                stream_info = stream.get("stream", {})
                enclosure.set("type", "application/x-bittorrent" if stream_info.get("type") == "torrent" else "application/x-nzb")
            
            # Torznab attributes
            torznab_ns = "{http://torznab.com/schemas/2015/feed}"
            
            # Category
            category = TorznabBuilder._determine_category(stream, query_type)
            attr = etree.SubElement(item, f"{torznab_ns}attr")
            attr.set("name", "category")
            attr.set("value", str(category))
            
            # Size attribute
            attr = etree.SubElement(item, f"{torznab_ns}attr")
            attr.set("name", "size")
            attr.set("value", str(size) if size else "0")
            
            # Seeders (for torrents)
            stream_info = stream.get("stream", {})
            if stream_info.get("type") == "torrent":
                seeders = stream_info.get("seeds", 0)
                attr = etree.SubElement(item, f"{torznab_ns}attr")
                attr.set("name", "seeders")
                attr.set("value", str(seeders))
                
                # Orionoid doesn't provide leechers, just use seeders as peers
                attr = etree.SubElement(item, f"{torznab_ns}attr")
                attr.set("name", "peers")
                attr.set("value", str(seeders))
            
            # InfoHash (for torrents)
            stream_info = stream.get("stream", {})
            if stream_info.get("type") == "torrent" and file_info.get("hash"):
                attr = etree.SubElement(item, f"{torznab_ns}attr")
                attr.set("name", "infohash")
                attr.set("value", file_info["hash"])
            
            # IMDb ID
            if meta_info.get("imdb"):
                attr = etree.SubElement(item, f"{torznab_ns}attr")
                attr.set("name", "imdbid")
                attr.set("value", meta_info["imdb"])
            
            # TVDB ID
            if meta_info.get("tvdb"):
                attr = etree.SubElement(item, f"{torznab_ns}attr")
                attr.set("name", "tvdbid")
                attr.set("value", str(meta_info["tvdb"]))
            
            # Season/Episode for TV
            if query_type == "tvsearch" and meta_info.get("episode"):
                episode_info = meta_info["episode"]
                if episode_info.get("season"):
                    attr = etree.SubElement(item, f"{torznab_ns}attr")
                    attr.set("name", "season")
                    attr.set("value", str(episode_info["season"]))
                
                if episode_info.get("episode"):
                    attr = etree.SubElement(item, f"{torznab_ns}attr")
                    attr.set("name", "episode")
                    attr.set("value", str(episode_info["episode"]))
            
            return item
            
        except Exception as e:
            # Log error and skip this item
            print(f"Error building item: {e}")
            return None
    
    @staticmethod
    def _determine_category(stream: Dict[str, Any], query_type: str) -> int:
        """Determine the appropriate category for a stream"""
        video_info = stream.get("video", {})
        quality = video_info.get("quality", "").lower()
        
        # Determine if it's a movie or TV show
        is_tv = query_type == "tvsearch" or stream.get("meta", {}).get("episode")
        
        # Determine quality level
        if "2160" in quality or "uhd" in quality or "4k" in quality:
            return TorznabBuilder.CATEGORY_TV_UHD if is_tv else TorznabBuilder.CATEGORY_MOVIE_UHD
        elif "1080" in quality or "720" in quality or "hd" in quality:
            return TorznabBuilder.CATEGORY_TV_HD if is_tv else TorznabBuilder.CATEGORY_MOVIE_HD
        elif "sd" in quality or "480" in quality:
            return TorznabBuilder.CATEGORY_TV_SD if is_tv else TorznabBuilder.CATEGORY_MOVIE_SD
        else:
            return TorznabBuilder.CATEGORY_TV if is_tv else TorznabBuilder.CATEGORY_MOVIE
    
    @staticmethod
    def build_error(code: int, description: str) -> str:
        """Build error XML response"""
        root = etree.Element("error")
        root.set("code", str(code))
        root.set("description", description)
        
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8').decode('utf-8')