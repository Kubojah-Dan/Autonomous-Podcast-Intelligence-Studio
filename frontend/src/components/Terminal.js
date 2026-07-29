import { useEffect, useRef } from "react";

const LEVEL_COLOR = {
  info: "#00FF41",
  warn: "#FFEB3B",
  error: "#FF006E",
};

export default function Terminal({ events, connected }) {
  const boxRef = useRef(null);

  useEffect(() => {
    if (boxRef.current) {
      boxRef.current.scrollTop = boxRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="border-4 border-black bg-black shadow-[8px_8px_0px_0px_#000] overflow-hidden">
      <div className="flex items-center justify-between bg-[#FF006E] text-white px-4 py-2 border-b-4 border-black">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 bg-black" />
          <span className="w-3 h-3 bg-black" />
          <span className="w-3 h-3 bg-black" />
          <span className="ml-3 font-display text-sm tracking-widest">AGENT_TERMINAL.LOG</span>
        </div>
        <span
          data-testid="pv-term-status"
          className={`text-xs font-bold uppercase tracking-widest ${connected ? "text-black" : "text-white/70"}`}
        >
          {connected ? "● LIVE" : "○ IDLE"}
        </span>
      </div>
      <div
        ref={boxRef}
        data-testid="pv-terminal"
        className="h-[400px] overflow-y-auto p-4 font-mono text-sm leading-relaxed"
      >
        {events.length === 0 && (
          <div className="text-[#00FF41]/60">
            $ awaiting job dispatch<span className="pv-cursor" />
          </div>
        )}
        {events.map((ev, i) => (
          <div key={i} className="whitespace-pre-wrap">
            {ev.type === "log" && (
              <>
                <span className="text-[#00FF41]/60">[{(ev.ts || "").slice(11, 19)}]</span>{" "}
                <span style={{ color: LEVEL_COLOR[ev.level] || "#00FF41" }}>
                  {ev.agent?.padEnd(14)}
                </span>
                <span className="text-[#00FF41]">│ {ev.message}</span>
              </>
            )}
            {ev.type === "milestone" && (
              <span className="text-[#FFEB3B]">◆ MILESTONE :: {ev.step} ({JSON.stringify({ ...ev, type: undefined, ts: undefined, step: undefined })})</span>
            )}
            {ev.type === "done" && (
              <span className="text-[#00FF41] font-bold">
                ═══ PIPELINE COMPLETE ═══
              </span>
            )}
            {ev.type === "error" && (
              <span className="text-[#FF006E] font-bold">!!! ERROR :: {ev.message}</span>
            )}
          </div>
        ))}
        {connected && events.length > 0 && (
          <div className="text-[#00FF41]">
            $<span className="pv-cursor" />
          </div>
        )}
      </div>
    </div>
  );
}
