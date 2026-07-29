import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/api";

const ROTS = ["rotate-[-1deg]", "rotate-[1deg]", "rotate-[-2deg]", "rotate-[2deg]"];

export default function Vault() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/vault")
      .then((r) => setItems(r.data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="pv-noise min-h-[calc(100vh-73px)] px-6 md:px-12 py-10">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-end justify-between mb-8">
          <div>
            <h1 className="font-display text-5xl md:text-7xl uppercase leading-none">
              THE <span className="pv-marker">VAULT</span>
            </h1>
            <p className="mt-3 font-mono text-sm">// every episode you've ever weaponized.</p>
          </div>
          <Link
            to="/"
            className="border-4 border-black bg-[#FFEB3B] px-4 py-2 font-bold uppercase tracking-widest text-sm shadow-[4px_4px_0px_0px_#000]"
          >
            + NEW
          </Link>
        </div>

        {loading && <div className="font-mono">loading...</div>}
        {!loading && items.length === 0 && (
          <div className="border-4 border-dashed border-black p-10 font-mono">
            <span className="text-black/60">
              // vault empty. head to the studio and ignite your first episode.
            </span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {items.map((it, i) => {
            const r = it.result || {};
            return (
              <Link
                key={it.id}
                to={`/episode/${it.id}`}
                data-testid={`pv-vault-tile-${i}`}
                className={`block border-4 border-black bg-white p-5 shadow-[8px_8px_0px_0px_#000] hover:shadow-[12px_12px_0px_0px_#FF006E] hover:-translate-y-1 transition-all ${ROTS[i % ROTS.length]}`}
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="border-2 border-black bg-black text-[#00FF41] px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest">
                    {it.id.slice(0, 8)}
                  </span>
                  <span
                    className={`border-2 border-black px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest ${
                      it.status === "complete"
                        ? "bg-[#00FF41]"
                        : it.status === "running"
                          ? "bg-[#FFEB3B]"
                          : "bg-[#FF006E] text-white"
                    }`}
                  >
                    {it.status}
                  </span>
                </div>
                <div className="font-display text-2xl uppercase leading-tight">
                  {r.title || it.title || "Untitled"}
                </div>
                <div className="mt-2 font-mono text-xs text-black/60 truncate">{it.url}</div>
                {(r.topics_count !== undefined || r.quotes_count !== undefined) && (
                  <div className="mt-4 flex gap-2 text-[10px] font-mono">
                    <span className="border-2 border-black bg-white px-2 py-0.5">
                      TOPICS {r.topics_count || 0}
                    </span>
                    <span className="border-2 border-black bg-white px-2 py-0.5">
                      QUOTES {r.quotes_count || 0}
                    </span>
                  </div>
                )}
                <div className="mt-4 font-mono text-[10px] text-black/60">
                  {new Date(it.created_at).toLocaleString()}
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
