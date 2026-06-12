import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api, clearToken, getToken, setToken } from "../api/client";
import type { AuthResponse, User } from "../api/types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (body: {
    company_name: string;
    email: string;
    password: string;
    full_name: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(getToken() !== null);

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/users/me"),
    enabled: hasToken,
    retry: false,
  });

  // An invalid/expired token must not lock the user on a blank screen
  if (hasToken && meQuery.isError) {
    clearToken();
    setHasToken(false);
  }

  const login = useCallback(
    async (email: string, password: string) => {
      const auth = await api<AuthResponse>("/auth/login", {
        method: "POST",
        body: { email, password },
      });
      setToken(auth.access_token);
      setHasToken(true);
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    [queryClient],
  );

  const signup = useCallback(
    async (body: { company_name: string; email: string; password: string; full_name: string }) => {
      const auth = await api<AuthResponse>("/auth/register", { method: "POST", body });
      setToken(auth.access_token);
      setHasToken(true);
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    [queryClient],
  );

  const logout = useCallback(() => {
    clearToken();
    setHasToken(false);
    queryClient.clear();
  }, [queryClient]);

  return (
    <AuthContext.Provider
      value={{
        user: hasToken ? (meQuery.data ?? null) : null,
        isLoading: hasToken && meQuery.isLoading,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit être utilisé sous AuthProvider");
  return context;
}
