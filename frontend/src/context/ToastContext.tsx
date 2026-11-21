import { useCallback, useMemo, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { ToastContext, type Toast } from "./toastContext";

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = useCallback((id: number) => setToasts((current) => current.filter((toast) => toast.id !== id)), []);
  const showToast = useCallback((message: string, tone: Toast["tone"] = "info") => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, message, tone }]);
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 4_500);
  }, []);
  const value = useMemo(() => ({ showToast }), [showToast]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" aria-live="polite" aria-relevant="additions text">
        {toasts.map((toast) => (
          <div className={`toast toast-${toast.tone}`} key={toast.id} role={toast.tone === "error" ? "alert" : "status"}>
            <span>{toast.message}</span>
            <button aria-label="Dismiss notification" onClick={() => dismiss(toast.id)}><X size={16} /></button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
