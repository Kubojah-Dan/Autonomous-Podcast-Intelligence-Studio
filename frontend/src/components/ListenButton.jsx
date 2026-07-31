import { useState, useRef } from "react";
import { api, BACKEND_URL } from "@/lib/api";
import { toast } from "sonner";

export function ListenButton({ text, artifactId, existingAudioUrl, profile = "narrator", label = "LISTEN" }) {
  const [state, setState] = useState("idle"); // idle | loading | playing | paused
  const audioRef = useRef(null);

  const handleClick = async () => {
    try {
      if (state === "idle") {
        setState("loading");
        let audioUrl = existingAudioUrl;
        if (!audioUrl) {
          const res = await api.post("/tts/synthesize", {
            text,
            profile,
            artifact_id: artifactId || "card",
          });
          audioUrl = res.data.audio_url;
        }

        const fullUrl = audioUrl.startsWith("http") ? audioUrl : `${BACKEND_URL}${audioUrl}`;
        const audio = new Audio(fullUrl);
        audioRef.current = audio;

        audio.onended = () => setState("idle");
        audio.onerror = () => {
          setState("idle");
          toast.error("> audio playback failed");
        };

        await audio.play();
        setState("playing");
      } else if (state === "playing") {
        if (audioRef.current) {
          audioRef.current.pause();
        }
        setState("paused");
      } else if (state === "paused") {
        if (audioRef.current) {
          await audioRef.current.play();
        }
        setState("playing");
      }
    } catch (e) {
      console.error("Audio synthesis/play error:", e);
      setState("idle");
      toast.error("> TTS synthesis failed");
    }
  };

  return (
    <button
      onClick={handleClick}
      type="button"
      className={`border-4 border-black font-mono uppercase font-bold text-xs px-4 py-2 transition-all shadow-[4px_4px_0px_0px_#000] hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none ${
        state === "playing"
          ? "bg-[#00FF41] text-black"
          : state === "loading"
          ? "bg-[#FFEB3B] text-black animate-pulse"
          : "bg-[#FF006E] text-white hover:bg-black"
      }`}
    >
      {state === "loading" ? "▮▮▮ SYNTHESIZING..." : state === "playing" ? "❚❚ PAUSE AUDIO" : `▶ ${label}`}
    </button>
  );
}
