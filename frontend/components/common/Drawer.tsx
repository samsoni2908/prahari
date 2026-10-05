"use client";

import React, { useEffect } from "react";
import { X } from "lucide-react";

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  badge?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: "md" | "lg" | "xl" | "full";
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  badge,
  children,
  footer,
  size = "lg",
}) => {
  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const sizeWidths = {
    md: "max-w-md",
    lg: "max-w-xl md:max-w-2xl",
    xl: "max-w-2xl md:max-w-4xl",
    full: "max-w-full",
  }[size];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-[#101D10]/50 backdrop-blur-sm transition-opacity duration-300 animate-in fade-in"
      />

      <div className="fixed inset-y-0 right-0 flex max-w-full pl-0 md:pl-10">
        <div
          className={`w-screen ${sizeWidths} bg-white shadow-modal flex flex-col border-l border-[#CFDDCE] animate-in slide-in-from-right duration-300`}
        >
          {/* Header */}
          <div className="px-5 py-4 border-b border-[#CFDDCE] bg-[#FAF9F5] flex items-center justify-between shrink-0">
            <div className="min-w-0 pr-4">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-serif text-lg font-bold text-[#182417] truncate">
                  {title}
                </h3>
                {badge}
              </div>
              {subtitle && (
                <div className="text-xs text-[#677766] mt-0.5">{subtitle}</div>
              )}
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#677766] hover:text-[#182417] hover:bg-[#EAF1E9] transition-colors shrink-0"
              aria-label="Close drawer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-5 md:p-6 bg-white space-y-5">
            {children}
          </div>

          {/* Footer */}
          {footer && (
            <div className="p-4 border-t border-[#CFDDCE] bg-[#FAF9F5] shrink-0">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: "sm" | "md" | "lg" | "xl";
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  footer,
  maxWidth = "md",
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) onClose();
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const widthClass = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
    xl: "max-w-2xl",
  }[maxWidth];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div
        onClick={onClose}
        className="fixed inset-0 bg-[#101D10]/50 backdrop-blur-sm transition-opacity"
      />
      <div
        className={`relative w-full ${widthClass} bg-white rounded-2xl border border-[#CFDDCE] shadow-modal overflow-hidden z-10 animate-in zoom-in-95 duration-200`}
      >
        <div className="px-6 py-4 border-b border-[#CFDDCE] bg-[#FAF9F5] flex items-center justify-between">
          <div>
            <h3 className="font-serif text-base font-bold text-[#182417]">{title}</h3>
            {subtitle && <p className="text-xs text-[#677766] mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#677766] hover:text-[#182417] hover:bg-[#EAF1E9]"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-6">{children}</div>
        {footer && <div className="px-6 py-3.5 border-t border-[#CFDDCE] bg-[#FAF9F5] flex justify-end gap-2">{footer}</div>}
      </div>
    </div>
  );
};
