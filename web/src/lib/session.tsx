"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { ApiError, api } from "./api";
import type { User } from "./types";

type SessionValue = {
  user: User | null;
  accessToken: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<boolean>;
  reloadUser: () => Promise<void>;
  authedFetch: <T>(path: string, init?: RequestInit) => Promise<T>;
};

const SessionContext = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const tokenRef = useRef<string | null>(null);

  const setToken = useCallback((token: string | null) => {
    tokenRef.current = token;
    setAccessToken(token);
  }, []);

  const loadUser = useCallback(
    async (token: string) => {
      const me = await api<User>("/api/v1/auth/me", {}, token);
      setToken(token);
      setUser(me);
    },
    [setToken],
  );

  const refresh = useCallback(async () => {
    try {
      const data = await api<{ access_token: string }>("/api/v1/auth/refresh", {
        method: "POST",
      });
      await loadUser(data.access_token);
      return true;
    } catch {
      setToken(null);
      setUser(null);
      return false;
    } finally {
      setLoading(false);
    }
  }, [loadUser, setToken]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await api<{ access_token: string }>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      await loadUser(data.access_token);
      setLoading(false);
    },
    [loadUser],
  );

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      await api("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
          display_name: displayName?.trim() || null,
        }),
      });
      await login(email, password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    try {
      await api("/api/v1/auth/logout", { method: "POST" });
    } finally {
      setToken(null);
      setUser(null);
    }
  }, [setToken]);

  const reloadUser = useCallback(async () => {
    const me = await api<User>("/api/v1/auth/me", {}, tokenRef.current);
    setUser(me);
  }, []);

  const authedFetch = useCallback(
    async <T,>(path: string, init: RequestInit = {}) => {
      try {
        return await api<T>(path, init, tokenRef.current);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          const ok = await refresh();
          if (ok) return api<T>(path, init, tokenRef.current);
        }
        throw error;
      }
    },
    [refresh],
  );

  const value = useMemo<SessionValue>(
    () => ({
      user,
      accessToken,
      loading,
      login,
      register,
      logout,
      refresh,
      reloadUser,
      authedFetch,
    }),
    [user, accessToken, loading, login, register, logout, refresh, reloadUser, authedFetch],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionValue {
  const context = useContext(SessionContext);
  if (context === null) {
    throw new Error("useSession must be used inside SessionProvider");
  }
  return context;
}
