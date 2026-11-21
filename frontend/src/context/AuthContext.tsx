import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setCsrfToken } from "../api/client";
import type { CurrentUser } from "../api/types";
import { AuthContext } from "./authContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const session = await api.getSession();
      setCsrfToken(session.csrf_token);
      setUser(session.user);
      setError(null);
    } catch (cause) {
      setCsrfToken("");
      setUser(null);
      const status = (cause as { status?: number }).status;
      setError(status === 401 ? null : cause instanceof Error ? cause.message : "Could not load your account.");
    } finally {
      setLoading(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      setCsrfToken("");
      setUser(null);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);
  const value = useMemo(() => ({ user, loading, error, refresh, signOut }), [user, loading, error, refresh, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
