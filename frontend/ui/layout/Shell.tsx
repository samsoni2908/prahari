"use client";

import React, { useState, useCallback } from "react";
import { useAuth } from "@/lib/auth-context";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import {
  LayoutDashboard,
  HeartPulse,
  AlertTriangle,
  Calendar,
  Users,
  Search,
  User,
  Settings,
} from "lucide-react";

interface ShellProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  children: React.ReactNode;
}

// Bottom nav items per role (4 key items for mobile)
const mobileNavConfig: Record<string, Array<{ id: string; label: string; icon: React.ElementType }>> = {
  PERSONNEL: [
    { id: "dashboard", label: "Home", icon: LayoutDashboard },
    { id: "wellbeing", label: "Wellness", icon: HeartPulse },
    { id: "leave", label: "Schedule", icon: Calendar },
    { id: "profile", label: "Profile", icon: User },
  ],
  COMMANDER: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "personnel", label: "Personnel", icon: Users },
    { id: "risk_trends", label: "Risk", icon: AlertTriangle },
    { id: "reports", label: "Reports", icon: Settings },
  ],
  WELFARE_OFFICER: [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "search", label: "Search", icon: Search },
    { id: "risk_monitor", label: "Risk", icon: AlertTriangle },
    { id: "assessments", label: "Wellness", icon: HeartPulse },
  ],
  ADMIN: [
    { id: "dashboard", label: "Home", icon: LayoutDashboard },
    { id: "users", label: "Users", icon: Users },
    { id: "units", label: "Units", icon: LayoutDashboard },
    { id: "system", label: "System", icon: Settings },
  ],
};

export const Shell: React.FC<ShellProps> = ({
  currentTab,
  onTabChange,
  children,
}) => {
  const { user } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const toggleMobileMenu = useCallback(() => {
    setIsMobileMenuOpen((prev) => !prev);
  }, []);

  const closeMobileMenu = useCallback(() => {
    setIsMobileMenuOpen(false);
  }, []);

  const navItems = (user && mobileNavConfig[user.role]) || [];

  return (
    <div className="min-h-screen flex flex-col bg-prahari-bg text-prahari-textPrimary font-sans">
      {/* Top Header */}
      <Header
        onMenuToggle={toggleMobileMenu}
        isMobileMenuOpen={isMobileMenuOpen}
      />

      {/* Main Body Area */}
      <div className="flex flex-1 relative overflow-hidden">
        {/* Desktop Sidebar */}
        <div className="hidden md:block shrink-0 h-[calc(100vh-4rem)] sticky top-16">
          <Sidebar currentTab={currentTab} onTabChange={onTabChange} />
        </div>

        {/* Mobile Slide-over Drawer Backdrop */}
        {isMobileMenuOpen && (
          <div
            className="md:hidden fixed inset-0 z-50 bg-black/50 backdrop-blur-sm transition-opacity"
            onClick={closeMobileMenu}
          >
            {/* Drawer */}
            <div
              className="w-64 h-full bg-white shadow-xl flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <Sidebar
                currentTab={currentTab}
                onTabChange={onTabChange}
                onClose={closeMobileMenu}
              />
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 pb-20 md:pb-8 min-w-0">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>

      {/* Mobile Bottom Navigation Bar (Phone-First Design) */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-prahari-border flex items-center justify-around h-14 px-2 shadow-lg"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`flex flex-col items-center justify-center flex-1 py-1 transition-colors ${
                isActive
                  ? "text-prahari-blue font-semibold"
                  : "text-prahari-textMuted hover:text-prahari-textPrimary"
              }`}
            >
              <Icon className="w-5 h-5 mb-0.5" />
              <span className="text-[10px] leading-tight">{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
};
