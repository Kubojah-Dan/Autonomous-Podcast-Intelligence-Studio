"""Voice Agent for PulseVault AI v2 — Text-to-Audio Layer.

Synthesizes any text artifact into audio using ElevenLabs or gTTS fallback.
Caches audio files under media/tts and provides audio playback URLs.
"""
import os
import logging
import hashlib
import asyncio
from pathlib import Path
from typing import Optional, Dict

log = logging.getLogger("pulsevault.voice")

MEDIA_DIR = Path(__file__).parent.parent / "media" / "tts"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

class VoiceAgent:
    """10th agent in the swarm — turns any text artifact into audio."""

    VOICE_PROFILES = {
        "narrator": "21m00Tcm4TlvDq8ikWAM",  # Rachel - warm narrator
        "punchy": "AZnzlk1XvdvUeBnXmlld",    # Domi - energetic
        "dramatic": "EXAVITQu4vr4xnSDxMAC",  # Bella - expressive
    }

    def __init__(self):
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")
        self.provider = os.environ.get("TTS_PROVIDER", "elevenlabs")

    async def synthesize(self, text: str, profile: str = "narrator", artifact_id: Optional[str] = None) -> Dict[str, str]:
        """Synthesize text to audio. Return dict with audio_url and cached path."""
        if not text or not text.strip():
            raise ValueError("text cannot be empty")

        clean_text = text.strip()
        # Hash text + profile to create unique cached filename
        text_hash = hashlib.md5(f"{clean_text}_{profile}".encode("utf-8")).hexdigest()[:12]
        filename = f"{artifact_id or 'tts'}_{text_hash}.mp3"
        filepath = MEDIA_DIR / filename
        relative_url = f"/media/tts/{filename}"

        if filepath.exists() and filepath.stat().st_size > 0:
            log.info(f"returning cached audio for artifact {artifact_id}: {filename}")
            return {"audio_url": relative_url, "path": str(filepath), "cached": True}

        # Try ElevenLabs first if key is present
        if self.api_key and self.provider == "elevenlabs":
            try:
                audio_bytes = await self._synthesize_elevenlabs(clean_text, profile)
                if audio_bytes:
                    with open(filepath, "wb") as f:
                        f.write(audio_bytes)
                    log.info(f"ElevenLabs synthesized audio saved: {filename}")
                    return {"audio_url": relative_url, "path": str(filepath), "cached": False}
            except Exception as e:
                log.warning(f"ElevenLabs TTS failed: {e}; falling back to gTTS")

        # Fallback: gTTS (Google Text-to-Speech)
        try:
            audio_bytes = await self._synthesize_gtts(clean_text)
            if audio_bytes:
                with open(filepath, "wb") as f:
                    f.write(audio_bytes)
                log.info(f"gTTS synthesized audio saved: {filename}")
                return {"audio_url": relative_url, "path": str(filepath), "cached": False}
        except Exception as e:
            log.warning(f"gTTS fallback failed: {e}; generating synthetic wave file")

        # Final Fallback: Generate synthetic silence/tone MP3 byte container if TTS libraries fail
        synthetic_bytes = self._generate_fallback_audio()
        with open(filepath, "wb") as f:
            f.write(synthetic_bytes)
        return {"audio_url": relative_url, "path": str(filepath), "cached": False}

    async def _synthesize_elevenlabs(self, text: str, profile: str) -> bytes:
        voice_id = self.VOICE_PROFILES.get(profile, self.VOICE_PROFILES["narrator"])
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        body = {
            "text": text[:3000],  # trim long text for API safety
            "model_id": "eleven_flash_v2_5",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        import httpx
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(url, headers=headers, json=body)
            resp.raise_for_status()
            return resp.content

    async def _synthesize_gtts(self, text: str) -> bytes:
        def _call():
            from gtts import gTTS
            import io
            tts = gTTS(text=text[:1500], lang="en", slow=False)
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            return fp.read()

        return await asyncio.to_thread(_call)

    def _generate_fallback_audio(self) -> bytes:
        """Fallback empty MP3 frame buffer."""
        # Minimal valid silence MP3 frame
        return b"\xff\xf3\x44\xc4\x00\x00\x00\x03\x48\x00\x00\x00\x00" * 200
