import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { toast } from "sonner";

const AGENTS = [
  { id: "AUDIO_INGEST", label: "AUDIO INGEST" },
  { id: "TRANSCRIBER", label: "TRANSCRIBER" },
  { id: "TOPIC_MINER", label: "TOPIC MINER" },
  { id: "QUOTE_HUNTER", label: "QUOTE HUNTER" },
  { id: "SHOW_NOTES", label: "SHOW NOTES" },
  { id: "SOCIAL_COPY", label: "SOCIAL COPY" },
  { id: "CLIP_CUTTER", label: "CLIP CUTTER" },
  { id: "SENTIMENT", label: "SENTIMENT MAP" },
  { id: "GUEST_RESEARCH", label: "GUEST RESEARCH" },
  { id: "CHAPTERS", label: "CHAPTERS GEN" },
  { id: "FACT_CHECK", label: "FACT CHECK★" },
  { id: "VOICE_AGENT", label: "VOICE AGENT★" },
];

const ROTATIONS = ["rotate-[-1deg]", "rotate-[1deg]", "rotate-[-2deg]", "rotate-[2deg]"];

export default function Landing() {
  const [url, setUrl] = useState("");
  const [customTitle, setCustomTitle] = useState("");
  const [demos, setDemos] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/demos").then((r) => setDemos(r.data)).catch(() => {});
  }, []);

  const detectPlatform = (val) => {
    const v = val.toLowerCase().trim();
    if (!v) return null;
    if (v.includes("youtube.com") || v.includes("youtu.be")) return { label: "▶ YOUTUBE", bg: "bg-red-500 text-white" };
    if (v.includes("spotify.com")) return { label: "🟢 SPOTIFY (METADATA + SEARCH)", bg: "bg-green-500 text-white" };
    if (v.includes("apple.com") || v.includes("podcasts.apple")) return { label: "🍎 APPLE PODCASTS", bg: "bg-purple-600 text-white" };
    if (v.includes("soundcloud.com")) return { label: "☁️ SOUNDCLOUD", bg: "bg-orange-500 text-white" };
    if (v.includes("feed") || v.endsWith(".xml") || v.endsWith(".rss")) return { label: "📻 RSS FEED", bg: "bg-[#FFEB3B] text-black" };
    if (v.endsWith(".mp3") || v.endsWith(".wav") || v.endsWith(".m4a") || v.endsWith(".ogg")) return { label: "🎵 DIRECT AUDIO", bg: "bg-[#00FF41] text-black" };
    return { label: "🌐 UNIVERSAL URL", bg: "bg-black text-white" };
  };

  const submit = async (payload) => {
    setSubmitting(true);
    try {
      const r = await api.post("/episode/ingest", payload);
      toast.success(`> job dispatched :: ${r.data.job_id.slice(0, 8)}`);
      navigate(`/episode/${r.data.job_id}`);
    } catch (e) {
      toast.error(`> ingest failed :: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file) return;
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (customTitle.trim()) {
        formData.append("title", customTitle.trim());
      }
      const r = await api.post("/episode/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(`> file uploaded & job dispatched :: ${r.data.job_id.slice(0, 8)}`);
      navigate(`/episode/${r.data.job_id}`);
    } catch (e) {
      toast.error(`> upload failed :: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (uploadFile) {
      handleFileUpload(uploadFile);
      return;
    }
    if (!url.trim()) {
      toast.error("> paste a podcast URL or select a local audio file first");
      return;
    }
    submit({ url: url.trim(), title: customTitle.trim() || undefined });
  };

  const runDemo = (d) => {
    submit({ url: d.url, demo_id: d.demo_id, title: d.title });
  };

  const platformInfo = detectPlatform(url);

  return (
    <div className="pv-noise min-h-[calc(100vh-73px)]">
      {/* Hero */}
      <section className="px-6 md:px-12 pt-12 md:pt-20 pb-10">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-wrap items-center gap-3 mb-6">
            <span className="border-4 border-black bg-[#FFEB3B] px-3 py-1 text-xs font-bold uppercase tracking-widest">
              v2.0 • AUDIO-NATIVE OPERATING SYSTEM
            </span>
            <span className="border-4 border-black bg-white px-3 py-1 text-xs font-bold uppercase tracking-widest">
              11 AGENTS • UNIVERSAL INGEST
            </span>
            <span className="border-4 border-black bg-black text-[#00FF41] px-3 py-1 text-xs font-bold uppercase tracking-widest">
              VOICE + TTS ACTIVE
            </span>
          </div>

          <h1 className="font-display text-5xl sm:text-7xl md:text-8xl leading-[0.9] uppercase">
            PODCAST <span className="pv-marker">INTELLIGENCE</span>
            <br />
            <span className="text-[#FF006E]">/</span>WEAPONIZED.
          </h1>
          <p className="mt-6 max-w-2xl text-base md:text-lg font-medium">
            Paste YouTube, Spotify, SoundCloud, Apple, RSS or upload MP3 files. 11 collaborative AI agents transcribe, mine topics,
            hunt viral quotes, draft SEO show-notes, cut vertical video clips, verify facts, and synthesize audio narration — <span className="pv-marker">in one shot</span>.
          </p>

          {/* URL & Title inputs */}
          <form onSubmit={handleSubmit} className="mt-10 space-y-4">
            <div>
              <label
                htmlFor="ep-title"
                className="block text-xs font-bold uppercase tracking-[0.2em] text-black/70 mb-1"
              >
                // Episode Title (Optional)
              </label>
              <input
                id="ep-title"
                type="text"
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
                placeholder="E.G. AESOP'S FABLES - VOLUME 1"
                className="w-full border-4 border-black bg-white px-4 py-3 text-base font-mono uppercase placeholder-black/30 shadow-[4px_4px_0px_0px_#000] focus:outline-none focus:shadow-[6px_6px_0px_0px_#FF006E]"
              />
            </div>

            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <label
                  htmlFor="ep-url"
                  className="block text-sm font-bold uppercase tracking-[0.2em] underline decoration-2 underline-offset-4"
                >
                  [&gt;_] Paste Universal Episode URL or Drop File
                </label>
                {platformInfo && (
                  <span className={`border-2 border-black px-3 py-0.5 font-mono text-xs font-bold uppercase ${platformInfo.bg}`}>
                    {platformInfo.label}
                  </span>
                )}
              </div>

              <div className="flex flex-col md:flex-row gap-4">
                <input
                  id="ep-url"
                  data-testid="pv-url-input"
                  type="text"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    if (uploadFile) setUploadFile(null);
                  }}
                  placeholder="YOUTUBE, SPOTIFY, APPLE, SOUNDCLOUD, RSS OR DIRECT MP3 URL"
                  className="flex-1 border-4 border-black bg-white px-6 py-6 text-lg md:text-xl font-mono uppercase placeholder-black/30 shadow-[8px_8px_0px_0px_#000] focus:outline-none focus:shadow-[12px_12px_0px_0px_#FF006E] transition-shadow"
                />
                <button
                  data-testid="pv-ingest-btn"
                  type="submit"
                  disabled={submitting}
                  className="border-4 border-black bg-[#FFEB3B] px-10 py-6 text-xl font-black uppercase tracking-widest shadow-[8px_8px_0px_0px_#000] hover:shadow-[12px_12px_0px_0px_#000] hover:-translate-x-1 hover:-translate-y-1 active:shadow-[4px_4px_0px_0px_#000] active:translate-x-1 active:translate-y-1 transition-all disabled:opacity-50"
                >
                  {submitting ? "DISPATCHING..." : "IGNITE →"}
                </button>
              </div>
            </div>

            {/* Local File Drag & Drop Zone */}
            <div className="border-4 border-dashed border-black bg-white p-6 shadow-[4px_4px_0px_0px_#000] text-center">
              <label className="cursor-pointer block">
                <span className="font-mono text-sm font-bold uppercase block mb-1">
                  📁 Or Click / Drag-and-Drop Local MP3/WAV Audio File Here
                </span>
                <span className="font-mono text-xs text-black/60 block">
                  {uploadFile ? `Selected: ${uploadFile.name}` : "Supports .mp3, .wav, .m4a, .ogg up to 3 hours cap"}
                </span>
                <input
                  type="file"
                  accept="audio/*"
                  onChange={(e) => {
                    if (e.target.files?.[0]) {
                      setUploadFile(e.target.files[0]);
                      setUrl(`file://${e.target.files[0].name}`);
                    }
                  }}
                  className="hidden"
                />
              </label>
            </div>
          </form>

          {/* Demo episodes */}
          <div className="mt-14">
            <h2 className="font-display text-2xl md:text-3xl uppercase mb-6">
              <span className="pv-marker">Preloaded</span> demos
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {demos.map((d, i) => (
                <button
                  key={d.demo_id}
                  data-testid={`pv-demo-${d.demo_id}`}
                  onClick={() => runDemo(d)}
                  disabled={submitting}
                  className={`text-left border-4 border-black bg-white shadow-[8px_8px_0px_0px_#000] p-6 hover:shadow-[12px_12px_0px_0px_#FF006E] hover:-translate-y-1 transition-all ${ROTATIONS[i % ROTATIONS.length]}`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <span className="border-2 border-black bg-[#FFEB3B] px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest">
                      DEMO / INSTANT
                    </span>
                    <span className="text-xs font-mono">#{String(i + 1).padStart(2, "0")}</span>
                  </div>
                  <div className="font-display text-2xl md:text-3xl uppercase leading-tight">
                    {d.title}
                  </div>
                  <div className="mt-3 text-sm font-mono">
                    <span className="text-black/60">host:</span> {d.host}
                    <br />
                    <span className="text-black/60">guest:</span> {d.guest}
                  </div>
                  <div className="mt-4 inline-block border-2 border-black bg-black text-[#00FF41] px-3 py-1 text-xs font-bold uppercase tracking-widest">
                    RUN AGENTS →
                  </div>
                </button>
              ))}
              {demos.length === 0 && (
                <div className="col-span-2 border-4 border-dashed border-black p-8 font-mono text-sm">
                  loading demos...
                </div>
              )}
            </div>
          </div>

          {/* Agents grid */}
          <div className="mt-20">
            <h2 className="font-display text-2xl md:text-3xl uppercase mb-6">
              The <span className="pv-marker">11-agent</span> swarm
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {AGENTS.map((a, i) => (
                <div
                  key={a.id}
                  className={`border-4 border-black bg-white p-4 shadow-[4px_4px_0px_0px_#000] ${
                    i % 3 === 0 ? "rotate-[-1deg]" : i % 3 === 1 ? "rotate-[1deg]" : ""
                  }`}
                >
                  <div className="text-[10px] font-mono text-black/60">AGENT_{String(i + 1).padStart(2, "0")}</div>
                  <div className="font-display uppercase text-sm md:text-base mt-1">{a.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Marquee footer stripe */}
      <div className="border-y-4 border-black bg-black overflow-hidden py-3">
        <div className="font-mono text-xs text-[#00FF41] uppercase tracking-[0.3em] whitespace-nowrap animate-marquee flex items-center gap-8">
          <span>/// PULSEVAULT AI v2 — 11-AGENT SWARM ACTIVE</span>
          <span>/// TEXT-TO-AUDIO LAYER (ELEVENLABS + gTTS)</span>
          <span>/// UNIVERSAL URL INGEST + SPOTIFY CROSS-REF</span>
          <span>/// PODCAST 2.0 CHAPTER MARKERS EXPORT</span>
          <span>/// FACT CHECK & TRUTH GUARD</span>
        </div>
      </div>
    </div>
  );
}
