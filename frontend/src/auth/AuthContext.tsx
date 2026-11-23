import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { UNAUTHORIZED_EVENT, apiFetch, getCsrf } from "../api/client";

export type RoleAssignment = {
  role: string;
  role_id: string;
  is_system: boolean;
  scope_type: string;
  scope_ref_id: string | null;
  institution_id: string | null;
};

export type User = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  institution: string | null;
  campus: string | null;
  is_staff: boolean;
  is_active: boolean;
  roles: RoleAssignment[];
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

  const refresh = useCallback(async () => {
    try {
      const res = await apiFetch<{ user: User }>("/auth/me/");
      setUser(res.user);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      await getCsrf().catch(() => null);
      const res = await apiFetch<{ user: User }>("/auth/login/", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setUser(res.user);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Login failed");
      setUser(null);
      throw cause;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await apiFetch<void>("/auth/logout/", { method: "POST" });
    } catch {
      setError(null);
    } finally {
      setUser(null);
      setError(null);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getCsrf().catch(() => null).finally(() => void refresh());
  }, [refresh]);

  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null);
      setLoading(false);
      setError("Your session has expired. Sign in again.");
    };
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, login, logout, refresh }),
    [user, loading, error, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
