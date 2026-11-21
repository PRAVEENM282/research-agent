import { createContext } from "react";

export type Toast = { id: number; message: string; tone: "success" | "error" | "info" };
export type ToastContextValue = { showToast: (message: string, tone?: Toast["tone"]) => void };
export const ToastContext = createContext<ToastContextValue | null>(null);
