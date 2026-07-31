import { BACKEND_URL } from "@/lib/api";
import { ListenButton } from "@/components/ListenButton";

export function ChaptersView({ chapters = [], jobId }) {
  if (!chapters || chapters.length === 0) {
    return (
      <div className="border-4 border-dashed border-black p-8 font-mono text-sm">
        <span className="text-black/60">// no chapter markers generated yet.</span>
      </div>
    );
  }

  const downloadUrl = `${BACKEND_URL}/api/episode/${jobId}/chapters.txt`;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-4 border-black bg-[#FFEB3B] p-6 shadow-[6px_6px_0px_0px_#000]">
        <div>
          <h2 className="font-display text-2xl uppercase">PODCAST 2.0 CHAPTER MARKERS</h2>
          <p className="font-mono text-xs text-black/80 mt-1">
            Auto-generated topic shifts & timestamps. Export as standard .chapters.txt for Apple, Spotify & YouTube.
          </p>
        </div>
        {jobId && (
          <a
            href={downloadUrl}
            target="_blank"
            rel="noreferrer"
            className="border-4 border-black bg-black text-[#00FF41] px-5 py-3 font-mono font-bold text-xs uppercase tracking-widest shadow-[4px_4px_0px_0px_#000] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all text-center"
          >
            📥 DOWNLOAD .CHAPTERS.TXT
          </a>
        )}
      </div>

      <div className="space-y-4">
        {chapters.map((ch, idx) => (
          <div
            key={idx}
            className="border-4 border-black bg-white p-5 shadow-[4px_4px_0px_0px_#000] hover:shadow-[8px_8px_0px_0px_#000] transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
          >
            <div className="flex items-start gap-4">
              <span className="border-4 border-black bg-black text-[#FFEB3B] px-3 py-1 font-mono text-sm font-bold">
                {ch.timestamp || "00:00"}
              </span>
              <div>
                <h3 className="font-display text-xl uppercase leading-tight">{ch.title}</h3>
                {ch.summary && <p className="font-mono text-sm text-black/70 mt-1">{ch.summary}</p>}
              </div>
            </div>
            <ListenButton
              text={`Chapter: ${ch.title}. ${ch.summary || ''}`}
              artifactId={`ch_${idx}`}
              profile="narrator"
              label="LISTEN CHAPTER"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
