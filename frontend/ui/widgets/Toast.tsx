"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
  toast: {
    success: (msg: string) => void;
    error: (msg: string) => void;
    warning: (msg: string) => void;
    info: (msg: string) => void;
  };
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => { removeToast(id); }, 4500);
  }, [removeToast]);

  const toast = {
    success: (msg: string) => showToast(msg, "success"),
    error: (msg: string) => showToast(msg, "error"),
    warning: (msg: string) => showToast(msg, "warning"),
    info: (msg: string) => showToast(msg, "info"),
  };

  const borderColors: Record<ToastType, string> = {
    success: "#2E7D32",
    error: "#C62828",
    warning: "#F57C00",
    info: "#1565C0",
  };

  const iconColors: Record<ToastType, string> = {
    success: "#2E7D32",
    error: "#C62828",
    warning: "#F57C00",
    info: "#1565C0",
  };

  return (
    <ToastContext.Provider value={{ showToast, toast }}>
      {children}

      {/* Floating container */}
      <div
        className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none"
        style={{ maxWidth: "380px", width: "100%" }}
      >
        {toasts.map((t) => {
          const Icon = {
            success: CheckCircle2,
            error: XCircle,
            warning: AlertTriangle,
            info: Info,
          }[t.type];

          return (
            <div
              key={t.id}
              className="pointer-events-auto flex items-start gap-3 p-4 rounded-xl shadow-lg animate-slide-up"
              style={{
                background: "#FFFFFF",
                borderLeft: `4px solid ${borderColors[t.type]}`,
                borderTop: "1px solid #E2E8F0",
                borderRight: "1px solid #E2E8F0",
                borderBottom: "1px solid #E2E8F0",
                boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
              }}
            >
              <Icon
                className="w-5 h-5 shrink-0 mt-0.5"
                style={{ color: iconColors[t.type] }}
              />
              <p className="text-sm font-medium text-prahari-textPrimary flex-1 leading-snug">
                {t.message}
              </p>
              <button
                onClick={() => removeToast(t.id)}
                className="text-prahari-textMuted hover:text-prahari-textPrimary transition-colors shrink-0"
                aria-label="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return ctx;
}
