import { BrowserRouter, Routes, Route } from "react-router-dom";
import Landing from "@/pages/Landing";
import Episode from "@/pages/Episode";
import Vault from "@/pages/Vault";
import Nav from "@/components/Nav";
import { Toaster } from "sonner";
import "@/App.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#FAFAF7] text-black">
        <Nav />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/episode/:id" element={<Episode />} />
          <Route path="/vault" element={<Vault />} />
        </Routes>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#000",
              color: "#00FF41",
              border: "4px solid #000",
              borderRadius: 0,
              boxShadow: "8px 8px 0px 0px #FF006E",
              fontFamily: "JetBrains Mono, monospace",
            },
          }}
        />
      </div>
    </BrowserRouter>
  );
}
