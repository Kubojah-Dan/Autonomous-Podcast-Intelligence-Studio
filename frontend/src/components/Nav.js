import { Link, useLocation } from "react-router-dom";

const links = [
  { to: "/", label: "STUDIO" },
  { to: "/vault", label: "VAULT" },
];

export default function Nav() {
  const loc = useLocation();
  return (
    <nav
      data-testid="pv-nav"
      className="border-b-4 border-black bg-[#FAFAF7] px-6 md:px-10 py-4 flex items-center justify-between"
    >
      <Link to="/" data-testid="pv-logo" className="flex items-center gap-3">
        <span className="inline-block w-6 h-6 bg-[#FF006E] border-4 border-black" />
        <span className="font-display text-2xl md:text-3xl">PULSEVAULT<span className="text-[#FF006E]">/</span>AI</span>
      </Link>
      <div className="flex items-center gap-2 md:gap-4">
        {links.map((l) => {
          const active = loc.pathname === l.to;
          return (
            <Link
              key={l.to}
              to={l.to}
              data-testid={`pv-nav-${l.label.toLowerCase()}`}
              className={`px-4 py-2 border-4 border-black text-sm font-bold uppercase tracking-widest ${
                active ? "bg-black text-[#FFEB3B]" : "bg-white hover:bg-[#FFEB3B]"
              } transition-colors`}
            >
              {l.label}
            </Link>
          );
        })}
        <a
          href="https://console.groq.com"
          target="_blank"
          rel="noreferrer"
          className="hidden md:inline-block px-4 py-2 border-4 border-black bg-[#FF006E] text-white text-sm font-bold uppercase tracking-widest hover:bg-black"
          data-testid="pv-nav-external"
        >
          POWERED BY GROQ + GEMINI
        </a>
      </div>
    </nav>
  );
}
