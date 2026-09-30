
"use client";

import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl";
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = "lg",
}) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "unset";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !mounted) return null;

  const maxWidthPx = {
    sm: "384px",
    md: "448px",
    lg: "560px",
    xl: "672px",
    "2xl": "768px",
  }[maxWidth] || "560px";

  const modalNode = (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-4 animate-fade-in"
      style={{
        background: "rgba(24, 38, 22, 0.60)",
        backdropFilter: "blur(3px)",
        WebkitBackdropFilter: "blur(3px)",
      }}
    >
      {/* Backdrop click dismiss */}
      <div className="absolute inset-0" onClick={onClose} aria-label="Close backdrop" />

      <div
        className="relative w-full rounded-2xl overflow-hidden shadow-2xl animate-slide-up"
        style={{
          maxWidth: maxWidthPx,
          background: "#FFFFFF",
          border: "1px solid #D2DED0",
          boxShadow: "0 25px 60px -12px rgba(28, 40, 26, 0.35)",
          maxHeight: "calc(100vh - 2.5rem)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4 shrink-0"
          style={{
            background: "linear-gradient(90deg, #243D20 0%, #2E4F28 100%)",
            color: "#FFFFFF",
          }}
        >
          <div className="pr-4">
            <h2 className="text-base font-bold tracking-wide text-white">{title}</h2>
            {subtitle && (
              <p className="text-xs text-emerald-100/80 mt-0.5">{subtitle}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors shrink-0"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content with internal scroll */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 overscroll-contain">
          {children}
        </div>
      </div>
    </div>
  );

  return createPortal(modalNode, document.body);
};
