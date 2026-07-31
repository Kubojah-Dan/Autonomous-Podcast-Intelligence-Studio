import { ListenButton } from "@/components/ListenButton";

export function GuestOutreachView({ dossier = {}, host = "", guest = "" }) {
  const name = dossier.name || guest || "Guest Expert";
  const emailHint = dossier.contact_email_hint || "contact@domain.com (via Hunter.io)";
  const linkedin = dossier.linkedin_url || "https://linkedin.com/in/guest-profile";
  const talkingPoints = dossier.talking_points || [
    "Key insights on recent industry shifts",
    "Perspectives on long-term strategy",
    "Actionable takeaways for the audience",
  ];
  const pitchDraft = dossier.pitch_email_draft || (
    `Hi ${name},\n\n` +
    `I loved your insights on the podcast! I'd love to invite you for a follow-up interview on our studio.\n\n` +
    `Best regards,\n${host || 'Podcast Host'}`
  );

  return (
    <div className="space-y-6">
      <div className="border-4 border-black bg-black text-[#00FF41] p-6 shadow-[6px_6px_0px_0px_#000]">
        <h2 className="font-display text-2xl uppercase">GUEST DOSSIER & OUTREACH ENGINE</h2>
        <p className="font-mono text-xs text-white/80 mt-1">
          Automated guest contact discovery, bio synthesis, talking points, and narrated personalized outreach.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Dossier Card */}
        <div className="lg:col-span-5 border-4 border-black bg-white p-6 shadow-[6px_6px_0px_0px_#000]">
          <div className="border-2 border-black bg-[#FFEB3B] px-3 py-1 font-mono text-xs font-bold uppercase inline-block mb-3">
            GUEST PROFILE
          </div>
          <h3 className="font-display text-3xl uppercase leading-none">{name}</h3>
          <p className="font-mono text-xs text-black/70 mt-2">{dossier.bio || "Industry Expert & Featured Guest"}</p>

          <div className="mt-6 space-y-3 font-mono text-xs">
            <div className="border-l-4 border-black pl-3 py-1">
              <span className="font-bold uppercase text-black/60">CONTACT HINT:</span>
              <br />
              <span className="font-bold text-sm text-[#FF006E]">{emailHint}</span>
            </div>
            <div className="border-l-4 border-black pl-3 py-1">
              <span className="font-bold uppercase text-black/60">LINKEDIN PROFILE:</span>
              <br />
              <a href={linkedin} target="_blank" rel="noreferrer" className="underline font-bold text-blue-600">
                {linkedin}
              </a>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t-2 border-dashed border-black/30">
            <h4 className="font-display text-lg uppercase mb-2">RECENT TALKING POINTS</h4>
            <ul className="space-y-1.5 font-mono text-xs">
              {talkingPoints.map((tp, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="font-bold text-[#FF006E]">▸</span>
                  <span>{tp}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Pitch Email Draft */}
        <div className="lg:col-span-7 border-4 border-black bg-white p-6 shadow-[6px_6px_0px_0px_#000] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2 mb-4">
              <span className="border-2 border-black bg-black text-[#00FF41] px-3 py-1 font-mono text-xs font-bold uppercase tracking-widest">
                OUTREACH EMAIL DRAFT
              </span>
              <ListenButton text={pitchDraft} artifactId="pitch_email" profile="narrator" label="LISTEN PITCH" />
            </div>

            <pre className="whitespace-pre-wrap font-mono text-xs bg-gray-50 border-2 border-black p-4 rounded-sm leading-relaxed">
              {pitchDraft}
            </pre>
          </div>

          <div className="mt-6 pt-4 border-t-2 border-dashed border-black/30 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(pitchDraft);
                alert("Pitch email draft copied to clipboard!");
              }}
              className="border-4 border-black bg-[#FFEB3B] px-5 py-2.5 font-mono text-xs font-bold uppercase shadow-[4px_4px_0px_0px_#000] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none"
            >
              📋 COPY DRAFT
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
