"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Shield,
  LayoutDashboard,
  Users,
  Activity,
  HeartHandshake,
  Settings,
  LogOut,
  Calendar,
  Briefcase,
  TrendingUp,
  FileText,
  Search,
  AlertTriangle,
  Menu,
  X,
  Lock,
  Database,
  Sliders,
  CheckCircle2,
  Clock,
  UserCheck,
  ChevronRight,
  ShieldAlert,
} from "lucide-react";
import { authApi, getStoredRole, getStoredUser } from "@/lib/api";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [activeRole, setActiveRole] = useState<string>("COMMANDER");

  useEffect(() => {
    const role = getStoredRole();
    const user = getStoredUser();
    if (role) setActiveRole(role);
    if (user) setCurrentUser(user);

    // If pathname implies role, align
    if (pathname.startsWith("/commander")) setActiveRole("COMMANDER");
    else if (pathname.startsWith("/welfare")) setActiveRole("WELFARE_OFFICER");
    else if (pathname.startsWith("/personnel")) setActiveRole("PERSONNEL");
    else if (pathname.startsWith("/admin")) setActiveRole("ADMIN");
  }, [pathname]);

  const handleLogout = async () => {
    await authApi.logout();
    router.push("/login");
  };

  // If on landing or login page, render clean container without dashboard sidebar
  const isPublicPage = pathname === "/" || pathname === "/login";
  if (isPublicPage) {
    return (
      <div className="min-h-screen bg-[#FBFBF8] text-[#182417] flex flex-col">
        {children}
      </div>
    );
  }

  // Navigation items strictly per product role
  const getNavItems = () => {
    switch (activeRole) {
      case "PERSONNEL":
        return [
          { name: "My Dashboard", href: "/personnel", icon: LayoutDashboard },
          { name: "Service Profile", href: "/personnel?tab=profile", icon: Users },
          { name: "Deployments", href: "/personnel?tab=deployment", icon: Briefcase },
          { name: "Leave & Rest", href: "/personnel?tab=leave", icon: Calendar },
          { name: "Voluntary Self-Check", href: "/personnel?tab=wellbeing", icon: Activity },
          { name: "Strain & Trend", href: "/personnel?tab=risk", icon: TrendingUp },
          { name: "Support Requests", href: "/personnel?tab=support", icon: HeartHandshake },
          { name: "Privacy Ledger", href: "/personnel?tab=privacy", icon: Lock },
        ];
      case "COMMANDER":
        return [
          { name: "Operational Suite", href: "/commander", icon: LayoutDashboard },
          { name: "Unit Overview", href: "/commander?tab=unit", icon: Users },
          { name: "Personnel Status", href: "/commander?tab=personnel", icon: UserCheck },
          { name: "Deployment Load", href: "/commander?tab=deployments", icon: Briefcase },
          { name: "Leave & Roster", href: "/commander?tab=leave", icon: Calendar },
          { name: "Workload Strain", href: "/commander?tab=workload", icon: Activity },
          { name: "WSI Risk Trends", href: "/commander?tab=trends", icon: TrendingUp },
          { name: "Readiness Reports", href: "/commander?tab=reports", icon: FileText },
        ];
      case "WELFARE_OFFICER":
        return [
          { name: "Welfare Dashboard", href: "/welfare", icon: LayoutDashboard },
          { name: "Personnel Search", href: "/welfare?tab=search", icon: Search },
          { name: "Active Cases", href: "/welfare?tab=cases", icon: HeartHandshake },
          { name: "Risk Monitor", href: "/welfare?tab=risk", icon: TrendingUp },
          { name: "Assessments", href: "/welfare?tab=assessments", icon: Activity },
          { name: "Alerts & Signals", href: "/welfare?tab=alerts", icon: AlertTriangle },
          { name: "Welfare Actions", href: "/welfare?tab=actions", icon: ShieldAlert },
          { name: "Audit Reports", href: "/welfare?tab=reports", icon: FileText },
        ];
      case "ADMIN":
        return [
          { name: "System Dashboard", href: "/admin", icon: LayoutDashboard },
          { name: "User Accounts", href: "/admin?tab=users", icon: Users },
          { name: "Personnel Master", href: "/admin?tab=personnel", icon: UserCheck },
          { name: "Unit Master", href: "/admin?tab=units", icon: Briefcase },
          { name: "Data Health", href: "/admin?tab=data", icon: Database },
          { name: "Model Governance", href: "/admin?tab=system", icon: Sliders },
          { name: "Policy Config", href: "/admin?tab=settings", icon: Settings },
        ];
      default:
        return [];
    }
  };

  const navItems = getNavItems();

  const getRoleBadge = () => {
    switch (activeRole) {
      case "COMMANDER":
        return {
          label: "COMMANDER",
          badgeClass: "bg-[#2C5127] text-[#FAF9F5] border-[#46723F]",
          indicator: "bg-emerald-400",
        };
      case "WELFARE_OFFICER":
        return {
          label: "WELFARE OFFICER",
          badgeClass: "bg-[#4A2D5C] text-[#FAF9F5] border-[#6E4788]",
          indicator: "bg-purple-300",
        };
      case "PERSONNEL":
        return {
          label: "PERSONNEL (MEMBER)",
          badgeClass: "bg-[#1E4D2B] text-[#FAF9F5] border-[#3B7A4E]",
          indicator: "bg-emerald-300",
        };
      case "ADMIN":
        return {
          label: "SYSTEM ADMIN",
          badgeClass: "bg-[#7A5012] text-[#FAF9F5] border-[#A8711E]",
          indicator: "bg-amber-300",
        };
      default:
        return {
          label: activeRole,
          badgeClass: "bg-[#2C5127] text-white border-[#46723F]",
          indicator: "bg-emerald-400",
        };
    }
  };

  const badge = getRoleBadge();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#FBFBF8] text-[#182417]">
      {/* Sidebar - Desktop (Deep Defence Olive Theme) */}
      <aside className="hidden md:flex flex-col w-[250px] bg-[#1A3217] text-white border-r border-[#244320] shrink-0">
        {/* Brand Header */}
        <div className="h-16 flex items-center px-4 gap-3 border-b border-[#244320] bg-[#142612]">
          <div className="h-9 w-9 rounded-lg bg-[#2C5127] border border-[#46723F] flex items-center justify-center text-white shadow-sm">
            <Shield className="h-5 w-5 text-[#FAF9F5]" />
          </div>
          <div className="min-w-0">
            <div className="font-serif font-bold tracking-wider text-base text-[#FAF9F5] flex items-center gap-1.5">
              <span>PRAHARI</span>
              <span className={`h-2 w-2 rounded-full ${badge.indicator} animate-pulse`} />
            </div>
            <div className="text-[10px] text-[#A6C3A0] tracking-wider font-mono">
              SIH 26186 • DEFENCE WELFARE
            </div>
          </div>
        </div>

        {/* Role Identity Tag */}
        <div className="px-4 py-3 bg-[#172B15] border-b border-[#244320] flex items-center justify-between">
          <span
            className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border shadow-sm ${badge.badgeClass}`}
          >
            {badge.label}
          </span>
          <span className="text-[10px] text-[#A6C3A0] font-mono">SEC-LVL 4</span>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isExact = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isExact
                    ? "bg-[#2C5127] text-white border border-[#46723F] shadow-sm font-semibold"
                    : "text-[#D0E0CE] hover:bg-[#244320] hover:text-white"
                }`}
              >
                <Icon
                  className={`h-4 w-4 shrink-0 ${
                    isExact ? "text-[#FAF9F5]" : "text-[#8EA88C]"
                  }`}
                />
                <span className="truncate">{item.name}</span>
              </Link>
            );
          })}

          <div className="pt-4 mt-4 border-t border-[#244320]">
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-[#FCA5A5] hover:bg-red-950/40 hover:text-red-300 transition-colors"
            >
              <LogOut className="h-4 w-4 shrink-0" />
              <span>Log Out</span>
            </button>
          </div>
        </nav>

        {/* Footer Privacy Guarantee */}
        <div className="p-3.5 border-t border-[#244320] bg-[#142612]">
          <div className="flex items-center gap-2 text-[10px] text-[#A6C3A0]">
            <Lock className="h-3 w-3 text-[#22C55E] shrink-0" />
            <span className="truncate font-mono">Row-Level Privacy Active</span>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* TopBar */}
        <header className="h-16 bg-white border-b border-[#CFDDCE] px-4 md:px-6 flex items-center justify-between shrink-0 shadow-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 rounded-lg hover:bg-[#F3F2EB] text-[#3B4B3A]"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>

            <div className="flex items-center gap-2.5">
              <span
                className={`text-[11px] font-mono font-bold px-2.5 py-0.5 rounded border ${badge.badgeClass}`}
              >
                {badge.label}
              </span>
              <span className="text-xs text-[#677766] hidden sm:inline border-l border-[#CFDDCE] pl-2.5">
                Session:{" "}
                <strong className="text-[#182417]">
                  {currentUser?.username || "demo_session"}
                </strong>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-[#ECFDF5] border border-[#A7F3D0] text-[11px] text-[#15803D] font-mono font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-[#22C55E] animate-ping" />
              <span>LIVE SYSTEM</span>
            </div>

            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#FAF9F5] hover:bg-[#F3F2EB] border border-[#CFDDCE] text-xs font-medium text-[#3B4B3A] transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="md:hidden bg-[#1A3217] text-white border-b border-[#244320] p-4 space-y-1.5 animate-in slide-in-from-top duration-200">
            <div className="pb-2 mb-2 border-b border-[#244320] flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-[#A6C3A0]">
                MENU • {badge.label}
              </span>
              <span className="text-xs text-[#A6C3A0]">
                {currentUser?.username || "Authenticated"}
              </span>
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-[#D0E0CE] hover:bg-[#244320] hover:text-white"
                >
                  <Icon className="h-4 w-4 text-[#8EA88C]" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium text-red-300 hover:bg-red-950/40"
            >
              <LogOut className="h-4 w-4" />
              <span>Logout</span>
            </button>
          </div>
        )}

        {/* Content Workspace (Warm Cream Palette) */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 bg-[#FBFBF8]">
          {children}
        </main>
      </div>
    </div>
  );
}
