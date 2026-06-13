import type { ComponentType } from "react";
import { NavLink } from "react-router-dom";

import type { UserRole } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../theme/ThemeContext";
import { Badge, type BadgeTone } from "./ui/Badge";
import { cn } from "./ui/cn";
import {
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Moon,
  Settings,
  Sparkles,
  Sun,
  UserIcon,
} from "./ui/icons";

const ROLE_LABELS: Record<UserRole, string> = {
  commercial: "Commercial",
  manager: "Manager",
  direction: "Direction",
};

const ROLE_TONES: Record<UserRole, BadgeTone> = {
  commercial: "blue",
  manager: "amber",
  direction: "emerald",
};

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
  roles?: UserRole[];
}

const NAV: NavItem[] = [
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/dashboard", label: "Équipe", icon: LayoutDashboard, roles: ["manager", "direction"] },
  { to: "/admin", label: "Administration", icon: Settings, roles: ["direction"] },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();

  if (!user) return null;

  const items = NAV.filter((item) => !item.roles || item.roles.includes(user.role));

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center gap-2 px-5 py-4">
        <Sparkles className="h-5 w-5 text-emerald-600" />
        <span className="text-lg font-semibold tracking-tight">
          SalesLoop <span className="text-emerald-600">AI</span>
        </span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-2">
        {items.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="space-y-2 border-t border-zinc-200 p-3 dark:border-zinc-800">
        <button
          onClick={toggle}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800"
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          {theme === "dark" ? "Thème clair" : "Thème sombre"}
        </button>

        <NavLink
          to="/profile"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors",
              isActive
                ? "bg-zinc-100 dark:bg-zinc-800"
                : "hover:bg-zinc-100 dark:hover:bg-zinc-800",
            )
          }
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
            <UserIcon className="h-4 w-4" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate font-medium text-zinc-800 dark:text-zinc-100">
              {user.full_name}
            </span>
            <Badge tone={ROLE_TONES[user.role]}>{ROLE_LABELS[user.role]}</Badge>
          </span>
        </NavLink>

        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
        >
          <LogOut className="h-4 w-4" />
          Déconnexion
        </button>
      </div>
    </aside>
  );
}
