"use client";

import React from "react";
import { useAuth } from "@/lib/auth-context";
import { Shield, LogOut, Menu, X } from "lucide-react";

interface HeaderProps {
  onMenuToggle?: () => void;
  isMobileMenuOpen?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onMenuToggle, isMobileMenuOpen }) => {
  const { user, logout } = useAuth();

  const roleLabel: Record<string, string> = {
    PERSONNEL: "Personnel",
    COMMANDER: "Commander",
    WELFARE_OFFICER: "Welfare Officer",
    ADMIN: "Administrator",
  };

  return (
    <header
      className="h-14 md:h-16 px-4 md:px-6 flex items-center justify-between sticky top-0 z-40 shrink-0 select-none"
      style={{
        background: "linear-gradient(90deg, #243D20 0%, #2E4F28 50%, #385E31 100%)",
        boxShadow: "0 2px 8px rgba(36, 61, 32, 0.20)",
        borderBottom: "1px solid rgba(255, 255, 255, 0.12)",
      }}
    >
      {/* Left: Hamburger (mobile) + Brand */}
      <div className="flex items-center gap-3">
        {/* Mobile menu toggle */}
        <button
          onClick={onMenuToggle}
          className="md:hidden text-white/80 hover:text-white p-1 rounded transition-colors"
          aria-label="Toggle menu"
          id="mobile-menu-toggle"
        >
          {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        {/* Shield + Brand */}
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: "rgba(255,255,255,0.18)", border: "1px solid rgba(255,255,255,0.25)" }}
          >
            <Shield className="w-4.5 h-4.5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-white tracking-widest text-sm md:text-base leading-none">
                SWASTI
              </span>
              <span
                className="hidden md:inline text-[10px] font-semibold px-1.5 py-0.5 rounded text-amber-200"
                style={{ background: "rgba(217, 142, 4, 0.25)", border: "1px solid rgba(217, 142, 4, 0.45)" }}
              >
                SIH 26186
              </span>
            </div>
            <div className="text-[10px] text-emerald-100/80 tracking-wider hidden md:block mt-0.5">
              DEFENCE WELFARE MONITOR
            </div>
          </div>
        </div>
      </div>

      {/* Right: User info */}
      <div className="flex items-center gap-2 md:gap-3">
        {user && (
          <>
            {/* User info (desktop) */}
            <div className="hidden md:block text-right mr-1">
              <div className="text-sm font-semibold text-white leading-tight">
                {user.full_name || user.username}
              </div>
              <div className="text-[11px] text-emerald-100/80 mt-0.5">
                {roleLabel[user.role] || user.role}
                {user.unit_code && (
                  <span className="ml-1.5 text-amber-200/90 font-mono">• {user.unit_code}</span>
                )}
              </div>
            </div>

            {/* Avatar */}
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
              style={{ background: "rgba(255,255,255,0.22)", border: "1px solid rgba(255,255,255,0.30)" }}
            >
              {(user.full_name || user.username)?.charAt(0)?.toUpperCase() || "U"}
            </div>

            {/* Logout */}
            <button
              onClick={() => logout()}
              id="header-logout-btn"
              title="Sign Out"
              className="p-2 rounded-lg text-white/70 hover:text-white hover:bg-white/10 transition-all ml-1"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </>
        )}
      </div>
    </header>
  );
};
