import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

const ROLE_LABELS = { commercial: "Commercial", manager: "Manager", direction: "Direction" };

function navClass({ isActive }: { isActive: boolean }): string {
  return `rounded-md px-3 py-1.5 text-sm font-medium ${
    isActive ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-200"
  }`;
}

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-6 py-3">
        <div className="flex items-center gap-8">
          <span className="text-lg font-semibold tracking-tight">
            SalesLoop <span className="text-emerald-600">AI</span>
          </span>
          {user && (
            <nav className="flex gap-1">
              <NavLink to="/chat" className={navClass}>
                Chat
              </NavLink>
              {(user.role === "manager" || user.role === "direction") && (
                <NavLink to="/dashboard" className={navClass}>
                  Équipe
                </NavLink>
              )}
              {user.role === "direction" && (
                <NavLink to="/admin" className={navClass}>
                  Admin
                </NavLink>
              )}
            </nav>
          )}
        </div>
        {user && (
          <div className="flex items-center gap-3 text-sm">
            <span className="text-zinc-700">{user.full_name}</span>
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500">
              {ROLE_LABELS[user.role]}
            </span>
            <button
              onClick={logout}
              className="rounded-md px-2 py-1 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800"
            >
              Déconnexion
            </button>
          </div>
        )}
      </header>
      <main className="min-h-0 flex-1">
        <Outlet />
      </main>
    </div>
  );
}
