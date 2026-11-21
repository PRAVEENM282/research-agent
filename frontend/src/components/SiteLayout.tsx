import { useState } from "react";
import { BookOpen, LogOut, Menu, Settings2, Shapes, Sparkles, X, History as HistoryIcon, Wrench } from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";

const primaryLinks = [
  { to: "/workspace", label: "Workspace", icon: Sparkles },
  { to: "/tasks", label: "Research runs", icon: HistoryIcon },
  { to: "/tools", label: "Tool connections", icon: Wrench },
];

const headings: Record<string, string> = {
  "/workspace": "Workspace",
  "/tasks": "Research runs",
  "/tools": "Tool connections",
  "/settings": "Settings",
  "/docs": "Documentation",
};

export function SiteLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  async function logout() {
    try { await signOut(); } finally { navigate("/login", { replace: true }); }
  }

  return (
    <div className="app-layout">
      <a className="skip-link" href="#main">Skip to content</a>
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`} aria-label="Main navigation">
        <NavLink to="/workspace" className="brand" onClick={() => setMenuOpen(false)}>
          <span className="brand-mark"><Shapes size={19} strokeWidth={2.1} /></span>
          <span>handoff</span>
        </NavLink>
        <div className="sidebar-label">WORKSPACE</div>
        <nav className="sidebar-nav">
          {primaryLinks.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} onClick={() => setMenuOpen(false)} className={({ isActive }) => `sidebar-link ${isActive ? "sidebar-link-active" : ""}`}>
              <Icon size={17} strokeWidth={1.8} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-bottom">
          <NavLink to="/docs" onClick={() => setMenuOpen(false)} className={({ isActive }) => `sidebar-link ${isActive ? "sidebar-link-active" : ""}`}>
            <BookOpen size={17} strokeWidth={1.8} /><span>Documentation</span>
          </NavLink>
          <NavLink to="/settings" onClick={() => setMenuOpen(false)} className={({ isActive }) => `sidebar-link ${isActive ? "sidebar-link-active" : ""}`}>
            <Settings2 size={17} strokeWidth={1.8} /><span>Settings</span>
          </NavLink>
          <div className="account-row">
            <span className="account-avatar">{(user?.display_name || user?.email || "H").slice(0, 1).toUpperCase()}</span>
            <span className="account-copy"><strong>{user?.display_name || "Researcher"}</strong><small>{user?.email}</small></span>
            <button className="account-menu" onClick={() => void logout()} aria-label="Sign out" title="Sign out"><LogOut size={15} /></button>
          </div>
        </div>
      </aside>

      {menuOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
      <div className="app-main">
        <header className="topbar">
          <button className="mobile-menu-button" aria-label={menuOpen ? "Close navigation" : "Open navigation"} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>
            {menuOpen ? <X size={19} /> : <Menu size={19} />}
          </button>
          <div className="breadcrumbs"><span>Handoff</span><span className="breadcrumb-slash">/</span><strong>{headings[location.pathname] || (location.pathname.startsWith("/tasks/") ? "Run details" : "Workspace")}</strong></div>
          <NavLink to="/settings" className="topbar-user" aria-label="Open settings"><span className="account-avatar account-avatar-small">{(user?.display_name || user?.email || "H").slice(0, 1).toUpperCase()}</span></NavLink>
        </header>
        <Outlet />
      </div>
    </div>
  );
}
