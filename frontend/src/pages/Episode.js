import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, wsUrl } from "@/lib/api";
import Terminal from "@/components/Terminal";
import { ListenButton } from "@/components/ListenButton";
import { ChaptersView } from "@/components/ChaptersView";
import { FactCheckView } from "@/components/FactCheckView";
import { ClipsView } from "@/components/ClipsView";
import { SentimentView } from "@/components/SentimentView";
import { GuestOutreachView } from "@/components/GuestOutreachView";
import { toast } from "sonner";

const TABS = [
  "OVERVIEW",
  "AUDIO & TTS",
  "CHAPTERS",
  "TOPICS & SENTIMENT",
  "QUOTES & CLIPS",
  "SHOW NOTES",
  "SOCIAL",
  "FACT CHECK",
  "GUEST & OUTREACH",
  "TRANSCRIPT",
];

export default function Episode() {
  const { id } = useParams();
  const [events, setEvents] = useState([]);
  const [episode, setEpisode] = useState(null);
  const [tab, setTab] = useState("OVERVIEW");
  const [connected, setConnected] = useState(false);
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleInput, setTitleInput] = useState("");
  const wsRef = useRef(null);

  useEffect(() => {
    api.get(`/episode/${id}`).then((r) => {
      setEpisode(r.data);
      setTitleInput(r.data?.result?.title || r.data?.title || "");
    }).catch(() => {});
  }, [id]);

  useEffect(() => {
    const ws = new WebSocket(wsUrl(`/api/agents/stream/${id}`));
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data);
        setEvents((prev) => [...prev, ev]);
        if (ev.type === "done") {
          api.get(`/episode/${id}`).then((r) => {
            setEpisode(r.data);
            setTitleInput(r.data?.result?.title || r.data?.title || "");
          });
          toast.success("> pipeline complete");
        }
        if (ev.type === "error") {
          toast.error(`> pipeline error :: ${ev.message}`);
        }
      } catch {}
    };
    return () => ws.close();
  }, [id]);

  const saveTitle = async () => {
    if (!titleInput.trim()) return;
    try {
      await api.patch(`/episode/${id}/title`, { title: titleInput.trim() });
      setEpisode((prev) => ({
        ...prev,
        title: titleInput.trim(),
        result: { ...(prev?.result || {}), title: titleInput.trim() },
      }));
      toast.success("> title updated & saved to DB");
      setEditingTitle(false);
    } catch (e) {
      toast.error("> failed to update title");
    }
  };

  const result = episode?.result || {};
  const running = episode?.status === "running";
  const displayTitle = result.title || episode?.title || "Untitled Episode";

  return (
    <div className="pv-noise min-h-[calc(100vh-73px)] px-6 md:px-12 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-3 flex-wrap">
              <span className="border-4 border-black bg-black text-[#00FF41] px-3 py-1 text-xs font-bold uppercase tracking-widest">
                JOB / {id.slice(0, 8)}
              </span>
              <span
                data-testid="pv-status"
                className={`border-4 border-black px-3 py-1 text-xs font-bold uppercase tracking-widest ${
                  running ? "bg-[#FFEB3B]" : episode?.status === "complete" ? "bg-[#00FF41]" : "bg-[#FF006E] text-white"
                }`}
              >
                {episode?.status || "loading"}
              </span>
              {result.platform && (
                <span className="border-4 border-black bg-white px-3 py-1 text-xs font-bold uppercase tracking-widest">
                  {result.platform}
                </span>
              )}
            </div>

            {editingTitle ? (
              <div className="flex items-center gap-2 max-w-2xl">
                <input
                  type="text"
                  value={titleInput}
                  onChange={(e) => setTitleInput(e.target.value)}
                  className="flex-1 border-4 border-black bg-white px-4 py-2 text-2xl md:text-4xl font-display uppercase shadow-[4px_4px_0px_0px_#000]"
                  autoFocus
                />
                <button
                  onClick={saveTitle}
                  className="border-4 border-black bg-[#00FF41] px-4 py-2 font-bold uppercase text-xs shadow-[4px_4px_0px_0px_#000]"
                >
                  SAVE
                </button>
                <button
                  onClick={() => {
                    setTitleInput(displayTitle);
                    setEditingTitle(false);
                  }}
                  className="border-4 border-black bg-white px-4 py-2 font-bold uppercase text-xs shadow-[4px_4px_0px_0px_#000]"
                >
                  CANCEL
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3 group flex-wrap">
                <h1 className="font-display text-4xl md:text-6xl uppercase leading-none">
                  {displayTitle}
                </h1>
                <button
                  onClick={() => {
                    setTitleInput(displayTitle);
                    setEditingTitle(true);
                  }}
                  className="border-2 border-black bg-white px-2 py-1 text-[10px] font-bold uppercase tracking-widest opacity-80 hover:opacity-100 hover:bg-[#FFEB3B]"
                  title="Rename Episode"
                >
                  ✏️ RENAME
                </button>
              </div>
            )}

            {(result.host || result.guest) && (
              <p className="mt-2 font-mono text-sm">
                host: <span className="font-bold">{result.host || "—"}</span> │ guest:{" "}
                <span className="font-bold">{result.guest || "—"}</span>
              </p>
            )}
          </div>
          <Link
            to="/"
            className="self-start border-4 border-black bg-white px-4 py-2 font-bold uppercase tracking-widest text-sm hover:bg-[#FFEB3B]"
          >
            ← NEW EPISODE
          </Link>
        </div>

        {/* DRM Warning Notice */}
        {result.drm_notice && (
          <div className="mb-8 border-4 border-black bg-[#FFEB3B] p-4 shadow-[6px_6px_0px_0px_#000] font-mono text-sm font-bold flex items-center justify-between">
            <span>⚠️ {result.drm_notice}</span>
          </div>
        )}

        {/* Grid: Terminal + Tabs */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <div className="lg:col-span-5">
            <Terminal events={events} connected={connected} />
            <div className="mt-4 border-4 border-black bg-white p-4 shadow-[4px_4px_0px_0px_#000]">
              <div className="text-xs font-bold uppercase tracking-widest mb-1">EVENTS LOGGED</div>
              <div className="font-mono text-2xl">{events.length}</div>
            </div>
          </div>

          <div className="lg:col-span-7">
            {/* Tabs */}
            <div className="flex flex-wrap gap-2 mb-4">
              {TABS.map((t) => (
                <button
                  key={t}
                  data-testid={`pv-tab-${t.replace(/\s/g, "-").toLowerCase()}`}
                  onClick={() => setTab(t)}
                  className={`border-4 border-black px-3 py-1.5 text-xs font-bold uppercase tracking-widest ${
                    tab === t ? "bg-black text-[#FFEB3B]" : "bg-white hover:bg-[#FFEB3B]"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>

            {tab === "OVERVIEW" && <Overview result={result} running={running} onOpenTranscript={() => setTab("TRANSCRIPT")} />}
            {tab === "AUDIO & TTS" && <AudioTab result={result} />}
            {tab === "CHAPTERS" && <ChaptersView chapters={result.chapters} jobId={id} />}
            {tab === "TOPICS & SENTIMENT" && (
              <div className="space-y-8">
                <Topics topics={result.topics} />
                <SentimentView sentiment={result.sentiment} />
              </div>
            )}
            {tab === "QUOTES & CLIPS" && (
              <div className="space-y-8">
                <Quotes quotes={result.quotes} />
                <ClipsView clips={result.clips} quotes={result.quotes} />
              </div>
            )}
            {tab === "SHOW NOTES" && <ShowNotes md={result.show_notes_md} title={displayTitle} />}
            {tab === "SOCIAL" && <Social social={result.social} title={displayTitle} />}
            {tab === "FACT CHECK" && <FactCheckView claims={result.claims} />}
            {tab === "GUEST & OUTREACH" && <GuestOutreachView dossier={result.guest_dossier} host={result.host} guest={result.guest} />}
            {tab === "TRANSCRIPT" && <TranscriptView transcript={result.transcript} preview={result.transcript_preview} running={running} />}
          </div>
        </div>
      </div>
    </div>
  );
}

function Empty({ label }) {
  return (
    <div className="border-4 border-dashed border-black p-8 font-mono text-sm">
      <span className="text-black/60">// {label} not ready yet. agents are still working...</span>
    </div>
  );
}

function Overview({ result, running, onOpenTranscript }) {
  if (!result?.title) return <Empty label="overview" />;
  const stats = [
    { k: "TRANSCRIPT", v: `${result.transcript_length || 0} chars` },
    { k: "TOPICS", v: (result.topics || []).length },
    { k: "QUOTES", v: (result.quotes || []).length },
    { k: "CHAPTERS", v: (result.chapters || []).length },
  ];
  const transcriptText = result.transcript || result.transcript_preview;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((s, i) => (
          <div
            key={s.k}
            className={`border-4 border-black bg-white p-4 shadow-[4px_4px_0px_0px_#000] ${
              i % 2 === 0 ? "rotate-[-1deg]" : "rotate-[1deg]"
            }`}
          >
            <div className="text-[10px] font-bold uppercase tracking-widest text-black/60">{s.k}</div>
            <div className="font-display text-2xl md:text-3xl">{s.v}</div>
          </div>
        ))}
      </div>

      {/* Briefing Player */}
      <div className="border-4 border-black bg-[#00FF41] p-6 shadow-[8px_8px_0px_0px_#000] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="border-2 border-black bg-black text-white px-2 py-0.5 font-mono text-[10px] font-bold uppercase">
            VOICE BRIEFING
          </span>
          <h3 className="font-display text-2xl uppercase mt-1">AUDIO SUMMARY NARRATION</h3>
          <p className="font-mono text-xs text-black/80">Listen to the AI narrator summarize the key takeaways of this recording.</p>
        </div>
        <ListenButton
          text={result.title ? `Overview for ${result.title}. ${result.show_notes_md || ''}` : "Episode Briefing"}
          artifactId="overview_narration"
          existingAudioUrl={result.overview_audio}
          profile="narrator"
          label="PLAY BRIEFING"
        />
      </div>

      <div className="border-4 border-black bg-white p-6 shadow-[8px_8px_0px_0px_#000]">
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-bold uppercase tracking-widest underline decoration-2 underline-offset-4">
            Transcript preview
          </div>
          {transcriptText && (
            <button
              onClick={onOpenTranscript}
              className="border-2 border-black bg-[#FFEB3B] px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest hover:bg-black hover:text-[#00FF41]"
            >
              VIEW FULL TRANSCRIPT TAB →
            </button>
          )}
        </div>
        <div className="font-mono text-sm leading-relaxed whitespace-pre-wrap max-h-64 overflow-y-auto pr-2 border-t-2 border-black/10 pt-3">
          {transcriptText || (running ? "transcribing..." : "no transcript")}
        </div>
      </div>
    </div>
  );
}

function AudioTab({ result }) {
  if (!result?.title) return <Empty label="audio & tts" />;

  return (
    <div className="space-y-6">
      <div className="border-4 border-black bg-black text-[#00FF41] p-6 shadow-[6px_6px_0px_0px_#000]">
        <h2 className="font-display text-2xl uppercase">TEXT-TO-AUDIO MULTIMODAL HUB</h2>
        <p className="font-mono text-xs text-white/80 mt-1">
          Every generated artifact in PulseVault AI v2 can be converted to high-fidelity audio narration.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="border-4 border-black bg-white p-6 shadow-[6px_6px_0px_0px_#000] flex flex-col justify-between">
          <div>
            <span className="border-2 border-black bg-[#FFEB3B] px-2 py-0.5 font-mono text-[10px] font-bold uppercase">
              EPISODE BRIEFING (NARRATOR)
            </span>
            <h3 className="font-display text-2xl uppercase mt-2">{result.title}</h3>
            <p className="font-mono text-xs text-black/70 mt-2">
              Full documentary-style audio narration of key topics & executive briefing.
            </p>
          </div>
          <div className="mt-6">
            <ListenButton
              text={`Briefing for ${result.title}. ${result.show_notes_md || ''}`}
              artifactId="audio_hub_briefing"
              existingAudioUrl={result.overview_audio}
              profile="narrator"
              label="LISTEN BRIEFING"
            />
          </div>
        </div>

        <div className="border-4 border-black bg-white p-6 shadow-[6px_6px_0px_0px_#000] flex flex-col justify-between">
          <div>
            <span className="border-2 border-black bg-[#FF006E] text-white px-2 py-0.5 font-mono text-[10px] font-bold uppercase">
              FEATURED QUOTE NARRATION
            </span>
            <h3 className="font-display text-2xl uppercase mt-2">
              "{result.quotes?.[0]?.quote || 'Viral Quote Moment'}"
            </h3>
            <p className="font-mono text-xs text-black/70 mt-2">
              Dramatic high-energy voice delivery of the top viral quote.
            </p>
          </div>
          <div className="mt-6">
            <ListenButton
              text={result.quotes?.[0]?.quote || "Featured viral quote"}
              artifactId="audio_hub_quote"
              existingAudioUrl={result.quote_audio}
              profile="dramatic"
              label="LISTEN QUOTE"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function TranscriptView({ transcript, preview, running }) {
  const fullText = transcript || preview;
  if (!fullText) return <Empty label="transcript" />;

  const copy = () => {
    navigator.clipboard.writeText(fullText);
    toast.success("> full transcript copied");
  };

  return (
    <div className="border-4 border-black bg-white shadow-[8px_8px_0px_0px_#000]">
      <div className="flex items-center justify-between border-b-4 border-black bg-[#00FF41] text-black px-4 py-2 flex-wrap gap-2">
        <div className="font-display uppercase text-sm tracking-widest">
          FULL UNTRUNCATED TRANSCRIPT ({fullText.length.toLocaleString()} CHARACTERS)
        </div>
        <button
          onClick={copy}
          className="border-2 border-black bg-white text-black px-3 py-1 text-[10px] font-bold uppercase tracking-widest hover:bg-[#FFEB3B]"
        >
          COPY TRANSCRIPT
        </button>
      </div>
      <div className="p-6 font-mono text-sm leading-relaxed whitespace-pre-wrap max-h-[600px] overflow-y-auto">
        {fullText}
      </div>
    </div>
  );
}

function Topics({ topics }) {
  if (!topics || topics.length === 0) return <Empty label="topics" />;
  return (
    <div className="space-y-4">
      <h2 className="font-display text-2xl uppercase border-b-4 border-black pb-2">TOPIC MINER OUTPUT</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {topics.map((t, i) => (
          <div
            key={i}
            data-testid={`pv-topic-${i}`}
            className={`border-4 border-black bg-white p-5 shadow-[6px_6px_0px_0px_#000] flex flex-col justify-between ${
              i % 2 === 0 ? "rotate-[-0.5deg]" : "rotate-[0.5deg]"
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="border-2 border-black bg-[#FFEB3B] px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest">
                  TOPIC / {String(i + 1).padStart(2, "0")}
                </span>
                {typeof t.importance === "number" && (
                  <span className="font-mono text-xs">■ {"█".repeat(Math.max(1, Math.min(10, t.importance)))}</span>
                )}
              </div>
              <div className="font-display text-xl md:text-2xl uppercase leading-tight">{t.topic}</div>
              <div className="mt-2 font-mono text-sm text-black/80">{t.summary}</div>
            </div>
            <div className="mt-4 pt-3 border-t-2 border-dashed border-black/30">
              <ListenButton text={`Topic: ${t.topic}. ${t.summary}`} artifactId={`topic_${i}`} profile="narrator" label="LISTEN TOPIC" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Quotes({ quotes }) {
  if (!quotes || quotes.length === 0) return <Empty label="quotes" />;
  const copy = (q) => {
    navigator.clipboard.writeText(`"${q.quote}" — ${q.speaker || "Unknown"}`);
    toast.success("> quote copied");
  };
  return (
    <div className="space-y-4">
      <h2 className="font-display text-2xl uppercase border-b-4 border-black pb-2">VIRAL QUOTES</h2>
      {quotes.map((q, i) => (
        <div
          key={i}
          data-testid={`pv-quote-${i}`}
          className="border-4 border-black bg-[#FFEB3B] p-5 shadow-[6px_6px_0px_0px_#000]"
        >
          <p className="font-display text-xl md:text-2xl leading-tight uppercase">"{q.quote}"</p>
          <div className="mt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="font-mono text-sm">
              — <span className="font-bold">{q.speaker || "Unknown"}</span>{" "}
              {q.punch && <span className="text-black/70">│ {q.punch}</span>}
            </div>
            <div className="flex items-center gap-2">
              <ListenButton text={q.quote} artifactId={`quote_${i}`} profile="dramatic" label="LISTEN" />
              <button
                onClick={() => copy(q)}
                className="border-4 border-black bg-white px-3 py-2 text-xs font-bold uppercase tracking-widest hover:bg-black hover:text-[#FFEB3B]"
              >
                COPY
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function MarkdownView({ content }) {
  if (!content) return null;
  const lines = content.split('\n');
  const elements = [];
  let listItems = [];

  const flushList = (key) => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${key}`} className="list-disc list-inside space-y-1.5 my-3 font-mono text-sm leading-relaxed">
          {listItems.map((item, idx) => (
            <li key={idx} className="pl-1">{formatInline(item)}</li>
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  const formatInline = (text) => {
    const parts = text.split(/(\*\*.*?\*\*|\[.*?\]\(.*?\))/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-bold text-black">{part.slice(2, -2)}</strong>;
      }
      const linkMatch = part.match(/^\[(.*?)\]\((.*?)\)$/);
      if (linkMatch) {
        return (
          <a key={i} href={linkMatch[2]} target="_blank" rel="noreferrer" className="underline font-bold text-[#FF006E] hover:bg-[#FFEB3B] px-1">
            {linkMatch[1]}
          </a>
        );
      }
      return part;
    });
  };

  lines.forEach((line, i) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
      listItems.push(trimmed.slice(2));
      return;
    }
    flushList(i);

    if (trimmed.startsWith('# ')) {
      elements.push(
        <h1 key={i} className="font-display text-3xl md:text-4xl uppercase border-b-4 border-black pb-2 mt-6 mb-4 leading-tight">
          {trimmed.slice(2)}
        </h1>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h2 key={i} className="font-display text-xl md:text-2xl uppercase border-b-2 border-black pb-1 mt-6 mb-3 text-[#FF006E]">
          {trimmed.slice(3)}
        </h2>
      );
    } else if (trimmed.startsWith('### ')) {
      elements.push(
        <h3 key={i} className="font-display text-lg uppercase font-bold mt-4 mb-2">
          {trimmed.slice(4)}
        </h3>
      );
    } else if (trimmed.startsWith('> ')) {
      elements.push(
        <blockquote key={i} className="border-l-4 border-black bg-[#FFEB3B]/40 p-4 font-mono text-sm my-3 font-semibold">
          {formatInline(trimmed.slice(2))}
        </blockquote>
      );
    } else if (trimmed.length > 0) {
      elements.push(
        <p key={i} className="font-mono text-sm leading-relaxed my-2">
          {formatInline(line)}
        </p>
      );
    }
  });
  flushList('final');

  return <div className="p-6 space-y-2">{elements}</div>;
}

function ShowNotes({ md, title }) {
  const [mode, setMode] = useState("RENDERED");
  if (!md) return <Empty label="show notes" />;
  const copy = () => {
    navigator.clipboard.writeText(md);
    toast.success("> markdown copied");
  };
  return (
    <div className="border-4 border-black bg-white shadow-[8px_8px_0px_0px_#000]">
      <div className="flex items-center justify-between border-b-4 border-black bg-[#FF006E] text-white px-4 py-3 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <span className="font-display uppercase text-sm tracking-widest">SHOWNOTES.MD</span>
          <div className="flex border-2 border-black bg-white text-black">
            <button
              onClick={() => setMode("RENDERED")}
              className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest ${
                mode === "RENDERED" ? "bg-black text-[#FFEB3B]" : "hover:bg-[#FFEB3B]"
              }`}
            >
              RENDERED
            </button>
            <button
              onClick={() => setMode("RAW")}
              className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest ${
                mode === "RAW" ? "bg-black text-[#FFEB3B]" : "hover:bg-[#FFEB3B]"
              }`}
            >
              RAW .MD
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ListenButton text={md} artifactId="show_notes" profile="narrator" label="LISTEN NOTES" />
          <button
            onClick={copy}
            className="border-2 border-black bg-white text-black px-3 py-1 text-[10px] font-bold uppercase tracking-widest hover:bg-[#FFEB3B]"
          >
            COPY .MD
          </button>
        </div>
      </div>
      {mode === "RENDERED" ? (
        <MarkdownView content={md} />
      ) : (
        <pre className="p-6 font-mono text-sm leading-relaxed whitespace-pre-wrap overflow-x-auto">
          {md}
        </pre>
      )}
    </div>
  );
}

function Social({ social, title }) {
  if (!social || Object.keys(social).length === 0) return <Empty label="social copy" />;
  const platforms = [
    { k: "twitter", label: "TWITTER / X", color: "bg-black text-white" },
    { k: "linkedin", label: "LINKEDIN", color: "bg-[#0077B5] text-white" },
    { k: "instagram", label: "INSTAGRAM", color: "bg-[#E4405F] text-white" },
  ];
  return (
    <div className="space-y-6">
      {platforms.map((p) => {
        const text = social[p.k];
        if (!text) return null;
        return (
          <div key={p.k} className="border-4 border-black bg-white shadow-[8px_8px_0px_0px_#000]">
            <div className={`flex items-center justify-between border-b-4 border-black px-4 py-2 ${p.color}`}>
              <span className="font-display uppercase text-sm tracking-widest">{p.label}</span>
              <div className="flex items-center gap-2">
                <ListenButton text={text} artifactId={`social_${p.k}`} profile="punchy" label="LISTEN CAPTION" />
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(text);
                    toast.success(`> ${p.k} caption copied`);
                  }}
                  className="border-2 border-black bg-white text-black px-3 py-1 text-[10px] font-bold uppercase tracking-widest hover:bg-[#FFEB3B]"
                >
                  COPY CAPTION
                </button>
              </div>
            </div>
            <pre className="p-6 font-mono text-sm leading-relaxed whitespace-pre-wrap">{text}</pre>
          </div>
        );
      })}
    </div>
  );
}
