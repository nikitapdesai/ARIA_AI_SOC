import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/alerts", label: "Alert Queue" },
  { to: "/analytics", label: "Analytics" },
  { to: "/live", label: "Live Analyze" },
  { to: "/incidents", label: "Incidents" },
  { to: "/knowledge-base", label: "Knowledge Base" },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <>
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className="rounded-md px-3 py-2 text-sm font-medium transition-colors hover:opacity-80"
          style={({ isActive }) => ({
            background: isActive ? "var(--surface-2)" : "transparent",
            color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
          })}
        >
          {item.label}
        </NavLink>
      ))}
    </>
  );
}

function Brand() {
  return (
    <div className="px-2 pb-6">
      <div className="text-lg font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
        ARIA
      </div>
      <div className="text-xs" style={{ color: "var(--text-muted)" }}>
        Alert Ranking &amp; Intelligence Agent
      </div>
    </div>
  );
}

export default function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setDrawerOpen(false), [location.pathname]);

  return (
    <div className="flex min-h-screen flex-col md:flex-row" style={{ background: "var(--page-plane)" }}>
      <div
        className="flex items-center justify-between border-b px-4 py-3 md:hidden"
        style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
      >
        <div className="text-base font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
          ARIA
        </div>
        <button
          onClick={() => setDrawerOpen(true)}
          aria-label="Open navigation"
          className="rounded-md border p-2"
          style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 6h18M3 12h18M3 18h18" strokeLinecap="round" />
          </svg>
        </button>
      </div>

      {drawerOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setDrawerOpen(false)} />
          <aside
            className="absolute left-0 top-0 h-full w-64 border-r px-4 py-6 flex flex-col gap-1"
            style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
          >
            <div className="mb-2 flex items-center justify-between px-2">
              <span className="text-lg font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>ARIA</span>
              <button
                onClick={() => setDrawerOpen(false)}
                aria-label="Close navigation"
                style={{ color: "var(--text-muted)" }}
              >
                ✕
              </button>
            </div>
            <NavLinks onNavigate={() => setDrawerOpen(false)} />
          </aside>
        </div>
      )}

      <aside
        className="hidden md:flex w-56 shrink-0 border-r px-4 py-6 flex-col gap-1"
        style={{ borderColor: "var(--border)", background: "var(--surface-1)" }}
      >
        <Brand />
        <NavLinks />
      </aside>

      <main className="flex-1 min-w-0 px-4 py-4 md:px-8 md:py-6">
        <Outlet />
      </main>
    </div>
  );
}
