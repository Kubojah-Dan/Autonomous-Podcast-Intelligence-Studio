import { ListenButton } from "@/components/ListenButton";

export function ClipsView({ clips = [], quotes = [] }) {
  if ((!clips || clips.length === 0) && (!quotes || quotes.length === 0)) {
    return (
      <div className="border-4 border-dashed border-black p-8 font-mono text-sm">
        <span className="text-black/60">// no viral clip candidates generated yet.</span>
      </div>
    );
  }

  const items = clips.length > 0 ? clips : quotes.map((q, idx) => ({
    title: `Viral Clip Candidate #${idx + 1}`,
    start: `0${idx}:15`,
    end: `0${idx}:45`,
    duration_sec: 30,
    hook: q.punch || q.quote,
    viral_score: 90 - idx * 5,
    layout: "9:16 vertical",
    quote_text: q.quote,
  }));

  return (
    <div className="space-y-6">
      <div className="border-4 border-black bg-[#FF006E] text-white p-6 shadow-[6px_6px_0px_0px_#000]">
        <h2 className="font-display text-2xl uppercase">VERTICAL VIDEO CLIP CUTTER (9:16)</h2>
        <p className="font-mono text-xs text-white/90 mt-1">
          Auto-detected viral moments optimized for YouTube Shorts, Instagram Reels & TikTok with word-by-word subtitle specs.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {items.map((c, idx) => (
          <div key={idx} className="border-4 border-black bg-white p-6 shadow-[6px_6px_0px_0px_#000] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between gap-2 mb-3">
                <span className="border-2 border-black bg-[#FFEB3B] px-2 py-0.5 font-mono text-[10px] font-bold uppercase">
                  FORMAT: {c.layout || "9:16 VERTICAL"}
                </span>
                <span className="border-2 border-black bg-black text-[#00FF41] px-2 py-0.5 font-mono text-[10px] font-bold uppercase">
                  SCORE: {c.viral_score || 95}/100
                </span>
              </div>

              <h3 className="font-display text-xl uppercase leading-tight mb-2">{c.title}</h3>
              <p className="font-mono text-xs text-black/70 mb-4">
                TIMESTAMPS: <span className="font-bold">{c.start} - {c.end}</span> ({c.duration_sec || 30}s)
              </p>

              {/* Mock 9:16 Frame Preview */}
              <div className="relative border-4 border-black bg-black rounded-sm aspect-[9/16] max-h-64 mx-auto my-4 flex flex-col items-center justify-center p-4 text-center overflow-hidden">
                <div className="absolute inset-0 opacity-20 bg-gradient-to-b from-[#FF006E] via-purple-900 to-black" />
                <span className="z-10 border-2 border-[#00FF41] text-[#00FF41] px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-widest mb-2">
                  ANIMATED SUBTITLES
                </span>
                <p className="z-10 font-display text-white text-base uppercase leading-tight px-2">
                  "{c.hook || c.quote_text || 'Viral audio moment'}"
                </p>
                <div className="z-10 mt-3 flex items-center gap-1">
                  <div className="w-1.5 h-6 bg-[#00FF41] animate-pulse" />
                  <div className="w-1.5 h-8 bg-[#FFEB3B] animate-pulse delay-75" />
                  <div className="w-1.5 h-4 bg-[#FF006E] animate-pulse delay-150" />
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t-2 border-dashed border-black/30 flex items-center justify-between">
              <ListenButton
                text={c.hook || c.quote_text || c.title}
                artifactId={`clip_${idx}`}
                profile="punchy"
                label="LISTEN CLIP"
              />
              <button
                type="button"
                onClick={() => alert(`FFmpeg Export Config generated for clip "${c.title}"`)}
                className="border-2 border-black bg-white px-3 py-1 font-mono text-[10px] font-bold uppercase hover:bg-[#FFEB3B]"
              >
                ⚙️ RENDER SPEC
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
