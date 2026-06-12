import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import type { UserRole } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export function Protected({ children, roles }: { children: ReactNode; roles?: UserRole[] }) {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/chat" replace />;
  return <>{children}</>;
}
