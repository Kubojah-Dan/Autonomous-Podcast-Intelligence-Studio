import pytest
import asyncio
from services.ingest_router import UniversalIngestRouter
from services.voice_agent import VoiceAgent

def test_ingest_router_demo():
    async def _test():
        router = UniversalIngestRouter()
        res = await router.resolve("demo://huberman-focus", custom_title="Custom Demo Title")
        assert res.kind == "demo"
        assert res.title == "Custom Demo Title"
    asyncio.run(_test())

def test_ingest_router_direct_audio():
    async def _test():
        router = UniversalIngestRouter()
        res = await router.resolve("https://example.com/podcast/episode123.mp3")
        assert res.kind == "direct_audio"
        assert res.audio_url == "https://example.com/podcast/episode123.mp3"
    asyncio.run(_test())

def test_voice_agent_fallback_synthesis():
    async def _test():
        agent = VoiceAgent()
        res = await agent.synthesize("Test podcast briefing text for PulseVault AI v2.", profile="narrator", artifact_id="test_art_01")
        assert "audio_url" in res
        assert res["audio_url"].startswith("/media/tts/")
    asyncio.run(_test())
