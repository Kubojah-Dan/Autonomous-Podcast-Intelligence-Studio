"""Universal Ingest Router for PulseVault AI v2.

Supports:
- YouTube, SoundCloud, Apple Podcasts, Vimeo, TikTok, Twitter/X via yt-dlp
- Direct audio URLs (.mp3, .wav, .m4a, .ogg)
- RSS feeds (xml/rss enclosure resolution)
- Spotify link metadata extraction + cross-reference matching
- File uploads
"""
import os
import re
import uuid
import logging
import asyncio
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any

import httpx
import feedparser

log = logging.getLogger("pulsevault.ingest")

class IngestResult:
    def __init__(
        self,
        kind: str,
        audio_url: Optional[str] = None,
        audio_path: Optional[str] = None,
        title: Optional[str] = None,
        host: Optional[str] = None,
        guest: Optional[str] = None,
        duration: Optional[int] = None,
        thumbnail: Optional[str] = None,
        source_platform: Optional[str] = None,
        drm_notice: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.kind = kind
        self.audio_url = audio_url
        self.audio_path = audio_path
        self.title = title
        self.host = host
        self.guest = guest
        self.duration = duration
        self.thumbnail = thumbnail
        self.source_platform = source_platform
        self.drm_notice = drm_notice
        self.metadata = metadata or {}


class UniversalIngestRouter:
    """Detects source platform and resolves audio stream / metadata."""

    def __init__(self):
        self.spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        self.spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        self.cookies_file = os.environ.get("YT_DLP_COOKIES_FILE")

    async def resolve(self, url: str, custom_title: Optional[str] = None) -> IngestResult:
        url_clean = url.strip()
        host = urlparse(url_clean).netloc.lower()

        # 1. Demo URL
        if url_clean.startswith("demo://"):
            return IngestResult(
                kind="demo",
                source_platform="demo",
                title=custom_title or "Demo Episode",
            )

        # 2. Upload / Local File
        if url_clean.startswith("upload://") or url_clean.startswith("file://") or os.path.exists(url_clean):
            file_path = url_clean.replace("upload://", "").replace("file://", "")
            return IngestResult(
                kind="file_upload",
                audio_path=file_path,
                source_platform="file_upload",
                title=custom_title or Path(file_path).stem.replace("_", " ").title(),
            )

        # 3. Spotify Link
        if "spotify.com" in host:
            return await self._resolve_spotify(url_clean, custom_title)

        # 4. Direct Audio URL
        path = urlparse(url_clean).path.lower()
        if any(path.endswith(ext) for ext in [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]):
            return IngestResult(
                kind="direct_audio",
                audio_url=url_clean,
                source_platform="direct_url",
                title=custom_title or Path(path).stem.replace("-", " ").replace("_", " ").title(),
            )

        # 5. RSS Feed
        if "feed" in url_clean or url_clean.endswith((".xml", ".rss")):
            rss_res = await self._resolve_rss(url_clean, custom_title)
            if rss_res:
                return rss_res

        # 6. Fallback to yt-dlp for YouTube, SoundCloud, Apple Podcasts, Vimeo, TikTok, etc.
        return await self._resolve_ytdlp(url_clean, custom_title)

    async def _resolve_spotify(self, url: str, custom_title: Optional[str]) -> IngestResult:
        log.info("processing Spotify link: fetching metadata and cross-referencing...")
        meta = await self._fetch_spotify_metadata(url)
        title = custom_title or meta.get("title") or "Spotify Podcast Episode"
        show_name = meta.get("show_name") or ""
        search_query = f"{title} {show_name}".strip()

        # Attempt to search YouTube for cross-reference audio
        yt_audio = await self._search_youtube_fallback(search_query)
        if yt_audio:
            log.info(f"successfully cross-referenced Spotify episode to YouTube: {yt_audio}")
            return IngestResult(
                kind="spotify_cross_ref",
                audio_url=yt_audio,
                title=title,
                host=meta.get("show_publisher"),
                thumbnail=meta.get("thumbnail"),
                source_platform="spotify",
                metadata=meta,
            )

        notice = (
            "Spotify-exclusive episodes are DRM-protected. We extracted episode metadata "
            f"('{title}'). For full audio transcription, upload the MP3 file or provide a YouTube / RSS URL."
        )
        return IngestResult(
            kind="spotify_metadata",
            title=title,
            host=meta.get("show_publisher"),
            thumbnail=meta.get("thumbnail"),
            source_platform="spotify",
            drm_notice=notice,
            metadata=meta,
        )

    async def _fetch_spotify_metadata(self, url: str) -> Dict[str, Any]:
        result = {"title": None, "show_name": None, "show_publisher": None, "thumbnail": None}
        if not self.spotify_client_id or not self.spotify_client_secret:
            return result

        try:
            async with httpx.AsyncClient(timeout=10) as http:
                # get access token
                token_resp = await http.post(
                    "https://accounts.spotify.com/api/token",
                    data={"grant_type": "client_credentials"},
                    auth=(self.spotify_client_id, self.spotify_client_secret),
                )
                if token_resp.status_code == 200:
                    token = token_resp.json().get("access_token")
                    # Extract episode ID
                    match = re.search(r"episode/([a-zA-Z0-9]+)", url)
                    if match:
                        ep_id = match.group(1)
                        ep_resp = await http.get(
                            f"https://api.spotify.com/v1/episodes/{ep_id}",
                            headers={"Authorization": f"Bearer {token}"},
                        )
                        if ep_resp.status_code == 200:
                            data = ep_resp.json()
                            result["title"] = data.get("name")
                            show = data.get("show") or {}
                            result["show_name"] = show.get("name")
                            result["show_publisher"] = show.get("publisher")
                            images = data.get("images") or show.get("images") or []
                            if images:
                                result["thumbnail"] = images[0].get("url")
        except Exception as e:
            log.warning(f"Spotify API metadata fetch failed: {e}")

        return result

    async def _search_youtube_fallback(self, query: str) -> Optional[str]:
        if not query or len(query) < 4:
            return None
        try:
            import yt_dlp
            ydl_opts = {
                "format": "bestaudio/best",
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "default_search": "ytsearch1",
            }
            if self.cookies_file and os.path.exists(self.cookies_file):
                ydl_opts["cookiefile"] = self.cookies_file

            def _search():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    res = ydl.extract_info(f"ytsearch1:{query}", download=False)
                    if res and "entries" in res and res["entries"]:
                        entry = res["entries"][0]
                        return f"https://www.youtube.com/watch?v={entry['id']}"
                return None

            return await asyncio.to_thread(_search)
        except Exception as e:
            log.warning(f"YouTube cross-reference search failed for '{query}': {e}")
            return None

    async def _resolve_rss(self, url: str, custom_title: Optional[str]) -> Optional[IngestResult]:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as http:
                resp = await http.get(url)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.text)
                    if feed.entries:
                        first = feed.entries[0]
                        title = custom_title or first.get("title") or feed.feed.get("title") or "RSS Podcast Episode"
                        enclosures = first.get("enclosures") or []
                        for enc in enclosures:
                            if enc.get("type", "").startswith("audio/") or enc.get("href", "").endswith((".mp3", ".m4a")):
                                return IngestResult(
                                    kind="rss_enclosure",
                                    audio_url=enc["href"],
                                    title=title,
                                    host=feed.feed.get("author") or feed.feed.get("publisher"),
                                    source_platform="rss",
                                )
        except Exception as e:
            log.warning(f"RSS feed parsing failed for {url}: {e}")
        return None

    async def _resolve_ytdlp(self, url: str, custom_title: Optional[str]) -> IngestResult:
        try:
            import yt_dlp
            opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
            }
            if self.cookies_file and os.path.exists(self.cookies_file):
                opts["cookiefile"] = self.cookies_file

            def _info():
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(url, download=False)

            info = await asyncio.to_thread(_info)
            platform = info.get("extractor_key") or "ytdlp"
            title = custom_title or info.get("title") or "Podcast Episode"
            duration = info.get("duration")
            thumbnail = info.get("thumbnail")

            return IngestResult(
                kind="ytdlp",
                audio_url=url,
                title=title,
                duration=duration,
                thumbnail=thumbnail,
                source_platform=platform.lower(),
            )
        except Exception as e:
            log.warning(f"yt-dlp metadata extraction failed for {url}: {e}")
            return IngestResult(
                kind="generic_url",
                audio_url=url,
                title=custom_title or "Podcast Episode",
                source_platform="url",
            )
