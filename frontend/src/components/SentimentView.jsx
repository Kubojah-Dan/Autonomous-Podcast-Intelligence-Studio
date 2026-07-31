export function SentimentView({ sentiment = [] }) {
  if (!sentiment || sentiment.length === 0) {
    return (
      <div className="border-4 border-dashed border-black p-8 font-mono text-sm">
        <span className="text-black/60">// emotional arc data mapping in progress...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="border-4 border-black bg-[#00FF41] text-black p-6 shadow-[6px_6px_0px_0px_#000]">
        <h2 className="font-display text-2xl uppercase">EMOTIONAL ARC & VIRAL PEAK MAPPER</h2>
        <p className="font-mono text-xs text-black/90 mt-1">
          Tracking emotional intensity, sentiment trajectory, and high-impact viral peaks throughout the episode.
        </p>
      </div>

      <div className="border-4 border-black bg-white p-6 shadow-[6px_6px_0px_0px_#000]">
        <h3 className="font-display text-xl uppercase mb-6">EPISODE INTENSITY TIMELINE</h3>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {sentiment.map((point, idx) => (
            <div
              key={idx}
              className={`border-4 border-black p-4 text-center relative ${
                point.is_viral_peak ? "bg-[#FF006E] text-white shadow-[4px_4px_0px_0px_#000]" : "bg-white text-black"
              }`}
            >
              {point.is_viral_peak && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 border-2 border-black bg-[#FFEB3B] text-black px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-widest">
                  🔥 VIRAL PEAK
                </span>
              )}
              <div className="font-mono text-xs font-bold mb-1">{point.timestamp || `0${idx}:00`}</div>
              <div className="font-display text-2xl uppercase">{point.intensity || 8}/10</div>
              <div className="font-mono text-[10px] uppercase font-bold mt-1 opacity-90">{point.emotion || "Insight"}</div>
              <div className="mt-2 text-[10px] font-mono border-t border-current pt-1">
                Score: {point.sentiment_score !== undefined ? point.sentiment_score : 0.75}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
