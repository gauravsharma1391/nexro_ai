import { useEffect, useState } from "react";
import { BarChart3, BrainCircuit, History as HistoryIcon, LayoutDashboard, LifeBuoy, Menu, MessageSquare, Moon, Settings as SettingsIcon, Sun, Type } from "lucide-react";
import { Logo } from "./ui";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import NLPLab from "./pages/NLPLab";
import DeepLearningLab from "./pages/DeepLearningLab";
import Analytics from "./pages/Analytics";
import ChatHistory from "./pages/ChatHistory";
import Settings from "./pages/Settings";
import Help from "./pages/Help";

const PAGES = [
  { id: "dashboard", label: "Overview", icon: LayoutDashboard },
  { id: "chat", label: "AI Chat", icon: MessageSquare },
  { id: "nlp", label: "NLP Lab", icon: Type },
  { id: "dl", label: "Deep Learning Lab", icon: BrainCircuit },
  { id: "analytics", label: "Analytics Studio", icon: BarChart3 },
  { id: "history", label: "Chat History", icon: HistoryIcon },
  { id: "settings", label: "Settings", icon: SettingsIcon },
  { id: "help", label: "Help", icon: LifeBuoy },
];

export default function App() {
  const [page, setPage] = useState(() => location.hash.slice(1) || "dashboard");
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem("nexora:theme") || "dark");

  useEffect(() => {
    const h = () => setPage(location.hash.slice(1) || "dashboard");
    window.addEventListener("hashchange", h);
    return () => window.removeEventListener("hashchange", h);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("nexora:theme", theme);
  }, [theme]);

  const go = (id: string) => { location.hash = id; setOpen(false); };
  const toggle = () => setTheme(theme === "dark" ? "light" : "dark");
  const view = {
    dashboard: <Dashboard go={go} />, chat: <Chat />, nlp: <NLPLab />, dl: <DeepLearningLab />,
    analytics: <Analytics />, history: <ChatHistory go={go} />, settings: <Settings theme={theme} toggle={toggle} />, help: <Help />,
  }[page] ?? <Dashboard go={go} />;

  return (
    <div className="app">
      <div className="topbar">
        <button className="btn ghost sm" aria-label="Open menu" onClick={() => setOpen(!open)}><Menu size={18} /></button>
        <Logo size={24} /> <b>Nexora AI</b>
      </div>
      <nav className={`side ${open ? "open" : ""}`} aria-label="Main">
        <div className="brand"><Logo /> Nexora AI</div>
        {PAGES.map((p) => (
          <button key={p.id} className={`nav ${page === p.id ? "on" : ""}`} aria-current={page === p.id ? "page" : undefined} onClick={() => go(p.id)}>
            <p.icon size={18} /> {p.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button className="nav" onClick={toggle}>{theme === "dark" ? <Sun size={18} /> : <Moon size={18} />} {theme === "dark" ? "Light theme" : "Dark theme"}</button>
      </nav>
      <main className="main">{view}</main>
    </div>
  );
}
