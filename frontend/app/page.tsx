"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Shield,
  Activity,
  HeartHandshake,
  Lock,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Users,
  Briefcase,
  TrendingUp,
  Cpu,
  Layers,
  FileCheck,
  Compass,
  AlertTriangle,
  ChevronRight,
  Calendar,
  Eye,
  Sliders,
  Sparkles,
} from "lucide-react";
import { getStoredRole, getStoredUser } from "@/lib/api";

export default function LandingPage() {
  const router = useRouter();
  const [activePreviewTab, setActivePreviewTab] = useState<"commander" | "welfare" | "personnel">("welfare");
  const [storedRole, setStoredRole] = useState<string | null>(null);

  useEffect(() => {
    const role = getStoredRole();
    if (role) setStoredRole(role);
  }, []);

  const getPortalRoute = () => {
    switch (storedRole) {
      case "COMMANDER":
        return "/commander";
      case "WELFARE_OFFICER":
        return "/welfare";
      case "PERSONNEL":
        return "/personnel";
      case "ADMIN":
        return "/admin";
      default:
        return "/login";
    }
  };

  return (
    <div className="min-h-screen bg-[#FBFBF8] text-[#182417] flex flex-col selection:bg-[#2C5127] selection:text-white">
      {/* ─── Top Navigation Header ───────────────────────────────────── */}
      <header className="sticky top-0 z-40 bg-[#FAF9F5]/90 backdrop-blur-md border-b border-[#CFDDCE] transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-[#2C5127] border border-[#46723F] flex items-center justify-center text-white shadow-sm">
              <Shield className="h-6 w-6 text-[#FAF9F5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif text-xl font-bold tracking-wider text-[#182417]">
                  PRAHARI
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#EAF1E9] text-[#2C5127] border border-[#CFDDCE] font-bold">
                  SIH 26186
                </span>
              </div>
              <p className="text-[10px] text-[#677766] tracking-wider uppercase font-mono">
                Personnel Welfare &amp; Readiness System
              </p>
            </div>
          </div>

          {/* Desktop Nav Links */}
          <nav className="hidden md:flex items-center gap-6 text-xs font-semibold text-[#3B4B3A]">
            <a href="#overview" className="hover:text-[#2C5127] transition-colors">
              Overview
            </a>
            <a href="#how-it-works" className="hover:text-[#2C5127] transition-colors">
              Core Loop
            </a>
            <a href="#capabilities" className="hover:text-[#2C5127] transition-colors">
              Capabilities
            </a>
            <a href="#roles" className="hover:text-[#2C5127] transition-colors">
              Four Roles
            </a>
            <a href="#privacy" className="hover:text-[#2C5127] transition-colors">
              Privacy Contract
            </a>
          </nav>

          {/* Action CTA */}
          <div className="flex items-center gap-3">
            <Link
              href={getPortalRoute()}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#2C5127] hover:bg-[#1E3A1A] active:bg-[#142612] text-white text-xs md:text-sm font-semibold tracking-wide shadow-sm shadow-[#2C5127]/20 border border-[#244320] transition-all"
            >
              <span>{storedRole ? "Enter Your Portal" : "Access Secure Portal"}</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      {/* ─── Hero Section ────────────────────────────────────────────── */}
      <section id="overview" className="relative overflow-hidden pt-12 pb-20 lg:pt-16 lg:pb-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            {/* Left Headline & Content */}
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#EAF1E9] border border-[#CFDDCE] text-xs font-mono text-[#2C5127]">
                <ShieldCheck className="h-4 w-4 text-[#15803D]" />
                <span className="font-bold">DEFENCE WELFARE DECISION SUPPORT</span>
              </div>

              <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#182417] leading-[1.15] tracking-tight">
                Privacy-Preserving Personnel Welfare &amp; Operational Workload Recovery.
              </h1>

              <p className="text-sm sm:text-base text-[#3B4B3A] leading-relaxed max-w-2xl">
                A governed decision-support platform for CAPFs and Armed Forces. Detects
                rising operational strain, explains workload and rest drivers, forecasts
                observable leave disruptions, and assists commanders in generating feasible,
                human-reviewed roster alternatives.
              </p>

              <div className="pt-2 flex flex-wrap gap-3">
                <Link
                  href="/login"
                  className="px-6 py-3.5 rounded-xl bg-[#2C5127] hover:bg-[#1E3A1A] text-white font-semibold text-sm shadow-md shadow-[#2C5127]/25 flex items-center gap-2 transition-all"
                >
                  <span>Authenticate Portal Access</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a
                  href="#how-it-works"
                  className="px-5 py-3.5 rounded-xl bg-white hover:bg-[#F6F7F3] text-[#182417] font-semibold text-sm border border-[#CFDDCE] shadow-sm transition-all"
                >
                  View Product Architecture
                </a>
              </div>

              {/* Integrity & Boundary Note */}
              <div className="pt-4 border-t border-[#E4ECE3] grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-[#677766]">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[#15803D] shrink-0" />
                  <span>Strictly Operational Decision Support</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[#15803D] shrink-0" />
                  <span>Not a Clinical Diagnosis System</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[#15803D] shrink-0" />
                  <span>Zero Raw Psychometrics to Command</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[#15803D] shrink-0" />
                  <span>Mandatory Human Accept/Modify/Reject</span>
                </div>
              </div>
            </div>

            {/* Right Visual Image */}
            <div className="lg:col-span-5 relative">
              <div className="relative rounded-2xl overflow-hidden border border-[#CFDDCE] shadow-xl bg-[#1A3217] aspect-[4/3] lg:aspect-auto lg:h-[480px]">
                <Image
                  src="/prahari/images/hero-force.webp"
                  alt="Defence personnel in mountain terrain at sunrise"
                  fill
                  priority
                  className="object-cover opacity-90"
                  sizes="(max-width: 1024px) 100vw, 40vw"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#142612]/90 via-[#1A3217]/30 to-transparent" />
                
                {/* Floating Operational Overlay Card */}
                <div className="absolute bottom-5 left-5 right-5 p-4 rounded-xl bg-white/95 backdrop-blur-md border border-[#CFDDCE] shadow-lg space-y-2 text-[#182417]">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-bold uppercase tracking-wider text-[#677766]">
                      Operational Loop
                    </span>
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-[#ECFDF5] text-[#15803D] font-bold border border-[#A7F3D0]">
                      Active Guard
                    </span>
                  </div>
                  <div className="text-sm font-bold font-serif">
                    Detect → Explain → Balance → Human Decision → Verify
                  </div>
                  <div className="text-[11px] text-[#3B4B3A]">
                    Transparent 7-factor Workload Strain Index (WSI) with Median/MAD personal baselining.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── The Core Product Loop (5 Stages) ────────────────────────── */}
      <section id="how-it-works" className="py-16 bg-[#FAF9F5] border-y border-[#CFDDCE]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center max-w-3xl mx-auto space-y-2">
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-[#2C5127]">
              GOVERNED DECISION PIPELINE
            </span>
            <h2 className="font-serif text-2xl sm:text-3xl lg:text-4xl font-bold text-[#182417]">
              How PRAHARI Operates
            </h2>
            <p className="text-xs sm:text-sm text-[#677766]">
              Every operational intervention follows a governed, auditable 5-stage loop.
              No automated or unilateral roster changes are ever executed without human review.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {/* Step 1 */}
            <div className="bg-white rounded-xl p-5 border border-[#CFDDCE] shadow-sm space-y-2 relative">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[#2C5127]">01</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#EAF1E9] text-[#2C5127] font-semibold">
                  DETECT
                </span>
              </div>
              <h4 className="font-serif text-base font-bold text-[#182417]">
                Workload Signal
              </h4>
              <p className="text-xs text-[#3B4B3A] leading-relaxed">
                Calculates the deterministic 7-factor WSI, personal Median/MAD baseline shift, and 30-day leave pattern anomaly risk.
              </p>
            </div>

            {/* Step 2 */}
            <div className="bg-white rounded-xl p-5 border border-[#CFDDCE] shadow-sm space-y-2 relative">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[#2C5127]">02</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#EAF1E9] text-[#2C5127] font-semibold">
                  EXPLAIN
                </span>
              </div>
              <h4 className="font-serif text-base font-bold text-[#182417]">
                Factor Drivers
              </h4>
              <p className="text-xs text-[#3B4B3A] leading-relaxed">
                Highlights understandable operational drivers: night duties, recovery deficits, consecutive shifts, and staffing constraints.
              </p>
            </div>

            {/* Step 3 */}
            <div className="bg-white rounded-xl p-5 border border-[#CFDDCE] shadow-sm space-y-2 relative">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[#2C5127]">03</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#EAF1E9] text-[#2C5127] font-semibold">
                  BALANCE
                </span>
              </div>
              <h4 className="font-serif text-base font-bold text-[#182417]">
                What-If Roster
              </h4>
              <p className="text-xs text-[#3B4B3A] leading-relaxed">
                Generates feasible roster adjustments checked against mandatory minimum rest, coverage, skills, and approved leave.
              </p>
            </div>

            {/* Step 4 */}
            <div className="bg-white rounded-xl p-5 border border-[#CFDDCE] shadow-sm space-y-2 relative border-l-4 border-l-[#B8860B]">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[#B8860B]">04</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-800 font-semibold border border-amber-200">
                  HUMAN CHOICE
                </span>
              </div>
              <h4 className="font-serif text-base font-bold text-[#182417]">
                Human Decision
              </h4>
              <p className="text-xs text-[#3B4B3A] leading-relaxed">
                An authorized commander or welfare officer reviews proposals and decides: <strong>ACCEPT</strong>, <strong>MODIFY</strong>, or <strong>REJECT</strong>.
              </p>
            </div>

            {/* Step 5 */}
            <div className="bg-white rounded-xl p-5 border border-[#CFDDCE] shadow-sm space-y-2 relative">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-[#2C5127]">05</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#EAF1E9] text-[#2C5127] font-semibold">
                  VERIFY
                </span>
              </div>
              <h4 className="font-serif text-base font-bold text-[#182417]">
                Measured Effect
              </h4>
              <p className="text-xs text-[#3B4B3A] leading-relaxed">
                Follows up over an approved observation window to measure whether operational strain and recovery indicators improved.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Interactive Product Preview Showcase ─────────────────────── */}
      <section className="py-16 bg-[#FBFBF8]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <span className="text-xs font-mono font-bold uppercase tracking-widest text-[#2C5127]">
                LIVE SYSTEM INTERFACES
              </span>
              <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[#182417] mt-1">
                Explore The Role Workspaces
              </h2>
            </div>

            {/* Tabs */}
            <div className="inline-flex p-1 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] shadow-sm text-xs font-medium">
              <button
                onClick={() => setActivePreviewTab("welfare")}
                className={`px-4 py-2 rounded-lg transition-all ${
                  activePreviewTab === "welfare"
                    ? "bg-[#2C5127] text-white font-semibold shadow-sm"
                    : "text-[#3B4B3A] hover:text-[#182417]"
                }`}
              >
                Welfare Officer
              </button>
              <button
                onClick={() => setActivePreviewTab("commander")}
                className={`px-4 py-2 rounded-lg transition-all ${
                  activePreviewTab === "commander"
                    ? "bg-[#2C5127] text-white font-semibold shadow-sm"
                    : "text-[#3B4B3A] hover:text-[#182417]"
                }`}
              >
                Commander
              </button>
              <button
                onClick={() => setActivePreviewTab("personnel")}
                className={`px-4 py-2 rounded-lg transition-all ${
                  activePreviewTab === "personnel"
                    ? "bg-[#2C5127] text-white font-semibold shadow-sm"
                    : "text-[#3B4B3A] hover:text-[#182417]"
                }`}
              >
                Personnel
              </button>
            </div>
          </div>

          {/* Interactive Preview Container */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] shadow-card overflow-hidden">
            {/* Header bar of preview */}
            <div className="px-6 py-3.5 border-b border-[#CFDDCE] bg-[#FAF9F5] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full bg-[#EF4444]/80" />
                <span className="h-3 w-3 rounded-full bg-[#F59E0B]/80" />
                <span className="h-3 w-3 rounded-full bg-[#22C55E]/80" />
                <span className="text-xs font-mono text-[#677766] ml-2">
                  PRAHARI // {activePreviewTab.toUpperCase()}_WORKSPACE
                </span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white border border-[#CFDDCE] text-[#677766]">
                Role-Gated Prototype View
              </span>
            </div>

            <div className="p-6 md:p-8">
              {activePreviewTab === "welfare" && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                      <span className="text-[11px] font-mono uppercase text-[#677766]">
                        Active Welfare Cases
                      </span>
                      <div className="text-2xl font-bold font-serif text-[#182417] mt-1">12</div>
                      <span className="text-[11px] text-[#15803D] font-mono">
                        4 scheduled for follow-up
                      </span>
                    </div>
                    <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                      <span className="text-[11px] font-mono uppercase text-[#677766]">
                        Attention Required
                      </span>
                      <div className="text-2xl font-bold font-serif text-[#B91C1C] mt-1">3</div>
                      <span className="text-[11px] text-[#677766] font-mono">
                        Consecutive night duties &gt; 4
                      </span>
                    </div>
                    <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                      <span className="text-[11px] font-mono uppercase text-[#677766]">
                        Privacy Mode
                      </span>
                      <div className="text-2xl font-bold font-serif text-[#15803D] mt-1">RLS Active</div>
                      <span className="text-[11px] text-[#677766] font-mono">
                        Derived indicators only
                      </span>
                    </div>
                  </div>

                  {/* Sample Personnel Dossier Row */}
                  <div className="p-5 rounded-xl border border-[#CFDDCE] bg-[#FAF9F5] space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-full bg-[#EAF1E9] text-[#2C5127] font-bold text-xs flex items-center justify-center border border-[#CFDDCE]">
                          HC
                        </div>
                        <div>
                          <div className="text-sm font-bold text-[#182417]">
                            HC Rajesh Kumar • Service #CRPF-89104
                          </div>
                          <div className="text-xs text-[#677766]">
                            Bravo Coy, 1-BN • Driver: Night duty concentration (7 shifts / 10 days)
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-full bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]">
                          Watch (WSI: 62)
                        </span>
                        <Link
                          href="/login"
                          className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-[#2C5127] text-white hover:bg-[#1E3A1A] transition-colors"
                        >
                          Open Dossier
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activePreviewTab === "commander" && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                      <span className="text-[11px] font-mono uppercase text-[#677766]">Unit Strength</span>
                      <div className="text-2xl font-bold font-serif text-[#182417] mt-1">128 / 135</div>
                      <span className="text-[11px] text-[#15803D] font-mono">94.8% Coverage</span>
                    </div>
                    <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                      <span className="text-[11px] font-mono uppercase text-[#677766]">Mean Unit WSI</span>
                      <div className="text-2xl font-bold font-serif text-[#182417] mt-1">37.4</div>
                      <span className="text-[11px] text-[#15803D] font-mono">Stable Band</span>
                    </div>
                    <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                      <span className="text-[11px] font-mono uppercase text-[#677766]">High Strain Alert</span>
                      <div className="text-2xl font-bold font-serif text-[#B91C1C] mt-1">2</div>
                      <span className="text-[11px] text-[#677766] font-mono">Action Recommended</span>
                    </div>
                    <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                      <span className="text-[11px] font-mono uppercase text-[#677766]">Roster Alternatives</span>
                      <div className="text-2xl font-bold font-serif text-[#2C5127] mt-1">3 Ready</div>
                      <span className="text-[11px] text-[#677766] font-mono">CP-SAT Formulated</span>
                    </div>
                  </div>
                </div>
              )}

              {activePreviewTab === "personnel" && (
                <div className="space-y-6">
                  <div className="p-5 rounded-xl border border-[#CFDDCE] bg-[#FAF9F5] space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Lock className="h-4 w-4 text-[#15803D]" />
                        <span className="text-xs font-mono font-bold text-[#182417] uppercase">
                          Private Voluntary Self-Check
                        </span>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                        Consent Active
                      </span>
                    </div>
                    <p className="text-xs text-[#3B4B3A]">
                      Your individual self-check answers are strictly confidential and stored under cryptographic row-level security.
                      Commanders receive zero raw question responses.
                    </p>
                    <div className="pt-2 flex items-center justify-between text-xs text-[#677766] border-t border-[#E4ECE3]">
                      <span>Last check-in: 3 days ago</span>
                      <Link
                        href="/login"
                        className="font-semibold text-[#2C5127] hover:underline"
                      >
                        Complete Self-Check →
                      </Link>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ─── The Four Application Roles ──────────────────────────────── */}
      <section id="roles" className="py-16 bg-[#FAF9F5] border-t border-[#CFDDCE]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div className="text-center max-w-3xl mx-auto space-y-2">
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-[#2C5127]">
              ACCESS CONTRACT
            </span>
            <h2 className="font-serif text-2xl sm:text-3xl lg:text-4xl font-bold text-[#182417]">
              Exactly Four Governed Roles
            </h2>
            <p className="text-xs sm:text-sm text-[#677766]">
              Designed around strict operational boundaries. Each role has access strictly bounded
              to its authorized duties.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Personnel */}
            <div className="bg-white rounded-2xl border border-[#CFDDCE] shadow-sm overflow-hidden flex flex-col justify-between">
              <div className="relative h-40 w-full bg-[#1A3217]">
                <Image
                  src="/prahari/images/mountain-patrol.webp"
                  alt="Personnel member on mountain patrol"
                  fill
                  className="object-cover opacity-80"
                  sizes="(max-width: 768px) 100vw, 25vw"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#142612] via-transparent to-transparent" />
                <div className="absolute bottom-3 left-4 text-white">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-900/80 border border-emerald-400/30 uppercase">
                    ROLE 01
                  </span>
                  <h4 className="font-serif text-lg font-bold mt-1">Personnel</h4>
                </div>
              </div>
              <div className="p-5 space-y-3 flex-1 flex flex-col justify-between text-xs">
                <p className="text-[#3B4B3A]">
                  Service members access their own duty ledger, leave balances, voluntary confidential self-reflection, and support requests.
                </p>
                <div className="pt-2 border-t border-[#E4ECE3] text-[11px] font-mono text-[#677766]">
                  Strict self-only data isolation
                </div>
              </div>
            </div>

            {/* Commander */}
            <div className="bg-white rounded-2xl border border-[#CFDDCE] shadow-sm overflow-hidden flex flex-col justify-between">
              <div className="relative h-40 w-full bg-[#1A3217]">
                <Image
                  src="/prahari/images/field-base.webp"
                  alt="Commanders reviewing operational field base"
                  fill
                  className="object-cover opacity-80"
                  sizes="(max-width: 768px) 100vw, 25vw"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#142612] via-transparent to-transparent" />
                <div className="absolute bottom-3 left-4 text-white">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-900/80 border border-blue-400/30 uppercase">
                    ROLE 02
                  </span>
                  <h4 className="font-serif text-lg font-bold mt-1">Commander</h4>
                </div>
              </div>
              <div className="p-5 space-y-3 flex-1 flex flex-col justify-between text-xs">
                <p className="text-[#3B4B3A]">
                  Receives unit-level operational readiness, aggregate WSI trends, factor explanations, and what-if roster balancing alternatives.
                </p>
                <div className="pt-2 border-t border-[#E4ECE3] text-[11px] font-mono text-[#677766]">
                  Zero individual psychometrics
                </div>
              </div>
            </div>

            {/* Welfare Officer */}
            <div className="bg-white rounded-2xl border border-[#CFDDCE] shadow-sm overflow-hidden flex flex-col justify-between">
              <div className="relative h-40 w-full bg-[#1A3217]">
                <Image
                  src="/prahari/images/medical-support.webp"
                  alt="Welfare officer conducting personnel support"
                  fill
                  className="object-cover opacity-80"
                  sizes="(max-width: 768px) 100vw, 25vw"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#142612] via-transparent to-transparent" />
                <div className="absolute bottom-3 left-4 text-white">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-900/80 border border-purple-400/30 uppercase">
                    ROLE 03
                  </span>
                  <h4 className="font-serif text-lg font-bold mt-1">Welfare Officer</h4>
                </div>
              </div>
              <div className="p-5 space-y-3 flex-1 flex flex-col justify-between text-xs">
                <p className="text-[#3B4B3A]">
                  Authorized individual welfare case management, 7-tab dossier, driver factors, follow-ups, and audit-logged interventions.
                </p>
                <div className="pt-2 border-t border-[#E4ECE3] text-[11px] font-mono text-[#677766]">
                  Governed welfare support path
                </div>
              </div>
            </div>

            {/* Admin */}
            <div className="bg-white rounded-2xl border border-[#CFDDCE] shadow-sm overflow-hidden flex flex-col justify-between">
              <div className="relative h-40 w-full bg-[#1A3217]">
                <Image
                  src="/prahari/images/monitoring-room.webp"
                  alt="Administrator monitoring secure system telemetry"
                  fill
                  className="object-cover opacity-80"
                  sizes="(max-width: 768px) 100vw, 25vw"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#142612] via-transparent to-transparent" />
                <div className="absolute bottom-3 left-4 text-white">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-900/80 border border-amber-400/30 uppercase">
                    ROLE 04
                  </span>
                  <h4 className="font-serif text-lg font-bold mt-1">Administrator</h4>
                </div>
              </div>
              <div className="p-5 space-y-3 flex-1 flex flex-col justify-between text-xs">
                <p className="text-[#3B4B3A]">
                  User management with Argon2id credentials, master records, system health, and RLS policy controls. Not a welfare superuser.
                </p>
                <div className="pt-2 border-t border-[#E4ECE3] text-[11px] font-mono text-[#677766]">
                  Strict system governance only
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Privacy By Design ───────────────────────────────────────── */}
      <section id="privacy" className="py-16 bg-[#FBFBF8] border-t border-[#CFDDCE]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          <div className="text-center max-w-2xl mx-auto space-y-2">
            <span className="text-xs font-mono font-bold uppercase tracking-widest text-[#2C5127]">
              ARCHITECTURAL GUARANTEE
            </span>
            <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[#182417]">
              Privacy &amp; Ethical Guardrails
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-6 rounded-2xl bg-white border border-[#CFDDCE] shadow-sm space-y-3">
              <div className="h-10 w-10 rounded-xl bg-[#EAF1E9] text-[#2C5127] flex items-center justify-center">
                <Lock className="h-5 w-5" />
              </div>
              <h3 className="font-serif text-base font-bold text-[#182417]">
                Zero Raw Answers to Command
              </h3>
              <p className="text-xs text-[#3B4B3A] leading-relaxed">
                Raw self-check responses remain strictly private to the individual service member.
                Commanders receive only unit-level operational readiness and recovery metrics.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white border border-[#CFDDCE] shadow-sm space-y-3">
              <div className="h-10 w-10 rounded-xl bg-[#EAF1E9] text-[#2C5127] flex items-center justify-center">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <h3 className="font-serif text-base font-bold text-[#182417]">
                No Punitive or Automated Decisions
              </h3>
              <p className="text-xs text-[#3B4B3A] leading-relaxed">
                PRAHARI never alters rosters automatically, never approves or denies leave unilaterally,
                and is never connected to promotions, postings, or disciplinary proceedings.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-white border border-[#CFDDCE] shadow-sm space-y-3">
              <div className="h-10 w-10 rounded-xl bg-[#EAF1E9] text-[#2C5127] flex items-center justify-center">
                <FileCheck className="h-5 w-5" />
              </div>
              <h3 className="font-serif text-base font-bold text-[#182417]">
                Truthful State &amp; Immutable Audit
              </h3>
              <p className="text-xs text-[#3B4B3A] leading-relaxed">
                Missing or stale telemetry is truthfully reported as INSUFFICIENT_DATA or MODEL_UNAVAILABLE.
                All recorded welfare actions are logged in an immutable audit ledger.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Final CTA Banner ────────────────────────────────────────── */}
      <section className="relative py-16 bg-[#1A3217] text-white overflow-hidden">
        <div className="absolute inset-0 opacity-20 pointer-events-none">
          <Image
            src="/prahari/images/sunset-patrol.webp"
            alt="Personnel silhouettes at sunset"
            fill
            className="object-cover"
          />
        </div>
        <div className="relative max-w-5xl mx-auto px-4 text-center space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-white/90 text-xs font-mono border border-white/20">
            <span>SMART INDIA HACKATHON 2024 • SIH 26186</span>
          </div>
          <h2 className="font-serif text-3xl sm:text-4xl font-bold leading-tight max-w-2xl mx-auto">
            Ready to Experience Governed Defence Personnel Decision Support?
          </h2>
          <p className="text-xs sm:text-sm text-[#D0E0CE] max-w-xl mx-auto leading-relaxed">
            Enter the portal with pre-configured demo credentials across Commander, Welfare Officer,
            Personnel, and Administrator roles.
          </p>
          <div className="pt-2">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-xl bg-[#FAF9F5] hover:bg-white text-[#1A3217] font-bold text-sm shadow-xl transition-all"
            >
              <span>Authenticate Portal Session</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ─── Site Footer ─────────────────────────────────────────────── */}
      <footer className="bg-[#142612] text-[#A6C3A0] py-12 border-t border-[#244320] text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-lg bg-[#2C5127] flex items-center justify-center text-white">
                <Shield className="h-5 w-5" />
              </div>
              <span className="font-serif text-lg font-bold text-white tracking-wider">
                PRAHARI
              </span>
              <span className="font-mono text-[10px] text-[#A6C3A0]">SIH 26186</span>
            </div>
            <div className="text-[11px] text-[#A6C3A0]">
              Personnel Stress &amp; Welfare Monitoring • Defence Decision Support Architecture
            </div>
          </div>

          <div className="pt-6 border-t border-[#244320] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[11px]">
            <span>© 2026 PRAHARI Initiative. All rights reserved.</span>
            <div className="flex items-center gap-4">
              <Link href="/login" className="hover:text-white transition-colors">
                Portal Login
              </Link>
              <a href="#privacy" className="hover:text-white transition-colors">
                Privacy Policy
              </a>
              <span className="text-[#677766]">PostgreSQL 16 • Next.js • FastAPI</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
