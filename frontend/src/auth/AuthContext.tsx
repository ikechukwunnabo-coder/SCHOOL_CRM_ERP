import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch, getCsrf } from "../api/client";

export type User = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  institution: string | null;
  campus: string | null;
  is_staff: boolean;
  is_active: boolean;
};

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    try {
      setError(null);
      const res = await apiFetch<{ user: User }>("/auth/me/");
      setUser(res.user);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Prime CSRF cookie for session-auth flows, then load session user
    getCsrf().catch(() => null).finally(() => void refresh());
  }, []);

  const login = async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      await getCsrf().catch(() => null);
      const res = await apiFetch<{ user: User }>("/auth/login/", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setUser(res.user);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Login failed";
      setError(msg);
      setUser(null);
      throw e;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await apiFetch<void>("/auth/logout/", { method: "POST" });
    } catch {
      // ignore
    } finally {
      setUser(null);
      setLoading(false);
    }
  };

  const value = useMemo(() => ({ user, loading, error, login, logout, refresh }), [user, loading, error]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
