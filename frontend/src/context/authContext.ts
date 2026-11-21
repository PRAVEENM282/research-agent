import { createContext } from "react";
import type { CurrentUser } from "../api/types";

export type AuthState = {
  user: CurrentUser | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
};

export const AuthContext = createContext<AuthState | null>(null);
