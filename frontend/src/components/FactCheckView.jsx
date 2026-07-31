export function FactCheckView({ claims = [] }) {
  if (!claims || claims.length === 0) {
    return (
      <div className="border-4 border-dashed border-black p-8 font-mono text-sm">
        <span className="text-black/60">// no factual claims extracted for verification yet.</span>
      </div>
    );
  }

  const getVerdictBadge = (verdict) => {
    const v = (verdict || "").toUpperCase();
    if (v.includes("VERIFIED")) {
      return "bg-[#00FF41] text-black border-black";
    }
    if (v.includes("CONTEXT")) {
      return "bg-[#FFEB3B] text-black border-black";
    }
    return "bg-[#FF006E] text-white border-black";
  };

  return (
    <div className="space-y-6">
      <div className="border-4 border-black bg-black text-white p-6 shadow-[6px_6px_0px_0px_#000]">
        <h2 className="font-display text-2xl uppercase text-[#00FF41]">FACT-CHECK & TRUTH GUARD</h2>
        <p className="font-mono text-xs text-white/80 mt-1">
          Automated extraction and verification of factual statements made during the recording.
        </p>
      </div>

      <div className="space-y-4">
        {claims.map((item, idx) => (
          <div key={idx} className="border-4 border-black bg-white p-6 shadow-[6px_6px_0px_0px_#000]">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <span className="font-mono text-xs text-black/60 uppercase font-bold">
                CLAIM #{String(idx + 1).padStart(2, "0")} │ SPEAKER: {item.speaker || "Unknown"}
              </span>
              <span className={`border-2 px-3 py-1 font-mono text-xs font-bold uppercase tracking-widest ${getVerdictBadge(item.verdict)}`}>
                {item.verdict || "NEEDS_CONTEXT"}
              </span>
            </div>

            <blockquote className="border-l-4 border-black pl-4 my-3 font-mono text-lg font-bold">
              "{item.claim}"
            </blockquote>

            {item.source && (
              <div className="mt-4 pt-3 border-t-2 border-dashed border-black/30 font-mono text-xs text-black/80">
                <span className="font-bold uppercase">Rationale / Source:</span> {item.source}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
