"use client";

import React from "react";
import { useAuth } from "@/lib/auth-context";
import {
  LayoutDashboard,
  User,
  MapPin,
  Calendar,
  HeartPulse,
  AlertTriangle,
  LifeBuoy,
  Settings,
  Users,
  Activity,
  FileText,
  Search,
  CheckCircle,
  Bell,
  Database,
  Server,
  Layers,
} from "lucide-react";
import clsx from "clsx";

interface SidebarProps {
  currentTab: string;
  onTabChange: (tabId: string) => void;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onTabChange, onClose }) => {
  const { user } = useAuth();

  if (!user) return null;

  // Exact menu configs matching AGENTS.md Section 11
  const menuConfig = {
    PERSONNEL: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "profile", label: "My Profile", icon: User },
      { id: "deployment", label: "Deployment", icon: MapPin },
      { id: "leave", label: "Leave", icon: Calendar },
      { id: "wellbeing", label: "Well-being", icon: HeartPulse },
      { id: "risk", label: "Risk Status", icon: AlertTriangle },
      { id: "support", label: "Support", icon: LifeBuoy },
      { id: "settings", label: "Settings", icon: Settings },
    ],
    COMMANDER: [
      { id: "overview", label: "Overview", icon: LayoutDashboard },
      { id: "unit_overview", label: "Unit Overview", icon: Layers },
      { id: "personnel", label: "Personnel", icon: Users },
      { id: "deployment", label: "Deployment", icon: MapPin },
      { id: "leave", label: "Leave", icon: Calendar },
      { id: "workload", label: "Workload", icon: Activity },
      { id: "risk_trends", label: "Risk Trends", icon: AlertTriangle },
      { id: "reports", label: "Reports", icon: FileText },
      { id: "settings", label: "Settings", icon: Settings },
    ],
    WELFARE_OFFICER: [
      { id: "overview", label: "Overview", icon: LayoutDashboard },
      { id: "search", label: "Search Personnel", icon: Search },
      { id: "personnel", label: "Personnel", icon: Users },
      { id: "risk_monitor", label: "Risk Monitor", icon: AlertTriangle },
      { id: "assessments", label: "Assessments", icon: HeartPulse },
      { id: "alerts", label: "Alerts", icon: Bell },
      { id: "actions", label: "Actions", icon: CheckCircle },
      { id: "reports", label: "Reports", icon: FileText },
      { id: "settings", label: "Settings", icon: Settings },
    ],
    ADMIN: [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "users", label: "Users", icon: Users },
      { id: "personnel", label: "Personnel", icon: User },
      { id: "units", label: "Units", icon: Layers },
      { id: "data_management", label: "Data Management", icon: Database },
      { id: "system", label: "System", icon: Server },
      { id: "settings", label: "Settings", icon: Settings },
    ],
  }[user.role] || [];

  const handleTabClick = (id: string) => {
    onTabChange(id);
    if (onClose) onClose(); // close mobile drawer
  };

  const roleLabel: Record<string, string> = {
    PERSONNEL: "Personnel",
    COMMANDER: "Commander",
    WELFARE_OFFICER: "Welfare Officer",
    ADMIN: "Administrator",
  };

  return (
    <aside
      className="w-64 flex flex-col h-full select-none"
      style={{ background: "#FFFFFF", borderRight: "1px solid #E1E8DF" }}
    >
      {/* User Info strip at top of sidebar */}
      <div
        className="px-4 py-4 flex items-center gap-3"
        style={{ borderBottom: "1px solid #E1E8DF" }}
      >
        <div
          className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
          style={{ background: "linear-gradient(135deg, #243D20, #385E31)" }}
        >
          {(user.full_name || user.username)?.charAt(0)?.toUpperCase() || "U"}
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold text-prahari-textPrimary truncate">
            {user.full_name || user.username}
          </div>
          <div className="text-xs text-prahari-textMuted truncate">
            {roleLabel[user.role] || user.role}
            {user.unit_code && ` • ${user.unit_code}`}
          </div>
        </div>
      </div>

      {/* Menu items */}
      <div className="flex-1 overflow-y-auto py-3 px-2">
        <div className="px-2 py-1.5 text-[10px] font-semibold uppercase tracking-widest text-prahari-textMuted mb-1">
          Navigation
        </div>

        {menuConfig.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;

          return (
            <button
              key={item.id}
              id={`sidebar-${item.id}`}
              onClick={() => handleTabClick(item.id)}
              className={clsx(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all text-left mb-0.5",
                isActive
                  ? "bg-[#EFF5EE] text-[#243D20] font-semibold border-l-4 border-[#385E31]"
                  : "text-prahari-textSecondary hover:bg-[#F5F8F4] hover:text-prahari-textPrimary"
              )}
            >
              <Icon
                className={clsx(
                  "w-4.5 h-4.5 shrink-0",
                  isActive ? "text-[#385E31]" : "text-prahari-textMuted"
                )}
                style={{ width: "18px", height: "18px" }}
              />
              <span className="truncate">{item.label}</span>
              {isActive && (
                <span
                  className="ml-auto w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: "#385E31" }}
                />
              )}
            </button>
          );
        })}
      </div>
    </aside>
  );
};
