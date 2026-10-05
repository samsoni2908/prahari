"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  ShieldCheck,
  HeartHandshake,
  Lock,
  CheckCircle,
  AlertCircle,
  Send,
  Calendar,
  Eye,
  RefreshCw,
  TrendingUp,
  User,
  Briefcase,
  Clock,
  CheckCircle2,
  FileText,
  Sliders,
  Award,
} from "lucide-react";
import { personnelApi } from "@/lib/api";
import { RiskBadge, StatusBadge } from "@/components/common/Badges";
import { StatCard } from "@/components/common/Cards";
import { Button } from "@/components/common/Button";
import { LoadingState, EmptyState } from "@/components/common/States";

export default function PersonnelPage() {
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "profile" | "duties" | "leave" | "wellbeing" | "support" | "privacy"
  >("dashboard");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // States
  const [profile, setProfile] = useState<any>(null);
  const [consent, setConsent] = useState<any>(null);
  const [riskData, setRiskData] = useState<any>(null);
  const [deployments, setDeployments] = useState<any[]>([]);
  const [duties, setDuties] = useState<any[]>([]);
  const [restRecords, setRestRecords] = useState<any[]>([]);
  const [leaves, setLeaves] = useState<any[]>([]);
  const [selfChecks, setSelfChecks] = useState<any[]>([]);
  const [supportRequests, setSupportRequests] = useState<any[]>([]);
  const [privacyHistory, setPrivacyHistory] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);

  // Support request form
  const [supportType, setSupportType] = useState("LEAVE_ASSISTANCE");
  const [supportPriority, setSupportPriority] = useState("NORMAL");
  const [supportDetails, setSupportDetails] = useState("");
  const [supportMsg, setSupportMsg] = useState<string | null>(null);
  const [submittingSupport, setSubmittingSupport] = useState(false);

  useEffect(() => {
    loadData();

    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get("tab");
      if (tab === "profile") setActiveTab("profile");
      else if (tab === "duties" || tab === "deployment") setActiveTab("duties");
      else if (tab === "leave") setActiveTab("leave");
      else if (tab === "wellbeing") setActiveTab("wellbeing");
      else if (tab === "support") setActiveTab("support");
      else if (tab === "privacy") setActiveTab("privacy");
      else if (tab === "dashboard" || tab === "risk") setActiveTab("dashboard");
    }
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [prof, cons, risk, deps, dut, rst, lv, reqs, priv, notifs] = await Promise.all([
        personnelApi.getProfile().catch(() => null),
        personnelApi.getConsent().catch(() => null),
        personnelApi.getMyRisk().catch(() => null),
        personnelApi.getMyDeployments().catch(() => []),
        personnelApi.getMyDuties().catch(() => []),
        personnelApi.getMyRest().catch(() => []),
        personnelApi.getMyLeave().catch(() => []),
        personnelApi.listSupportRequests().catch(() => []),
        personnelApi.getPrivacyHistory().catch(() => []),
        personnelApi.getNotifications().catch(() => []),
      ]);

      setProfile(prof);
      setConsent(cons);
      setRiskData(risk);
      setDeployments(deps || []);
      setDuties(dut || []);
      setRestRecords(rst || []);
      setLeaves(lv || []);
      setSupportRequests(reqs || []);
      setPrivacyHistory(priv || []);
      setNotifications(notifs || []);

      const checks = await personnelApi.listSelfChecks().catch(() => []);
      setSelfChecks(checks || []);
    } catch (err: any) {
      setError(err.message || "Failed to load personnel records");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleConsent() {
    setError(null);
    try {
      const action = consent?.consented ? "WITHDRAW" : "CONSENT";
      const res = await personnelApi.updateConsent(action);
      setConsent((prev: any) => ({ ...prev, consented: res.consented, status: res.status }));
    } catch (err: any) {
      setError(err.message);
    }
  }

  async function handleCreateSupportRequest(e: React.FormEvent) {
    e.preventDefault();
    if (!supportDetails) return;
    setSubmittingSupport(true);
    setSupportMsg(null);
    try {
      await personnelApi.createSupportRequest({
        request_type: supportType,
        priority: supportPriority,
        details: supportDetails,
      });
      setSupportMsg("Support request submitted confidentially to Welfare Officer.");
      setSupportDetails("");
      const refreshed = await personnelApi.listSupportRequests();
      setSupportRequests(refreshed || []);
    } catch (err: any) {
      setError(err.message || "Failed to submit support request");
    } finally {
      setSubmittingSupport(false);
    }
  }

  // Truthful strain status derivation without hardcoded scores
  const wsiValue: number | null = riskData?.wsi?.value ?? riskData?.current_risk_score ?? null;
  const wsiStatus: string = riskData?.wsi?.status ?? (wsiValue !== null ? "AVAILABLE" : "NOT_COMPUTED");
  const riskBand: "LOW" | "MEDIUM" | "HIGH" = (riskData?.risk_band as any) || (wsiValue !== null ? (wsiValue >= 70 ? "HIGH" : wsiValue >= 40 ? "MEDIUM" : "LOW") : "LOW");

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* ─── Header & Member Identity ─────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#CFDDCE]">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-serif text-2xl font-bold text-[#182417]">
              Personnel Welfare &amp; Service Portal
            </h1>
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#ECFDF5] border border-[#A7F3D0] text-[#15803D] font-bold">
              Confidential Self-View
            </span>
          </div>
          <p className="text-xs text-[#677766] mt-1 font-mono">
            Service ID:{" "}
            <strong className="text-[#182417]">
              {profile?.pseudo_id || "P-4401"}
            </strong>{" "}
            ({profile?.rank_or_grade || "Havildar"}) • Unit:{" "}
            {profile?.unit?.unit_name || "1-BN"}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadData()}
            disabled={loading}
            icon={<RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />}
          >
            Refresh
          </Button>

          <span className="px-3 py-1.5 rounded-full bg-[#FAF9F5] text-[#2C5127] text-xs font-semibold border border-[#CFDDCE] flex items-center gap-1.5">
            <Lock className="h-3.5 w-3.5 text-[#15803D]" />
            <span>RLS Isolated Session</span>
          </span>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-[#FEF2F2] text-[#B91C1C] border border-[#FECACA] text-xs flex items-center gap-2 animate-in fade-in">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ─── Tabs Navigation ─────────────────────────────────────────── */}
      <div className="flex border-b border-[#CFDDCE] space-x-2 overflow-x-auto">
        {[
          { id: "dashboard", label: "Strain & Status" },
          { id: "profile", label: "Service Profile" },
          { id: "duties", label: "Duties & Deployments" },
          { id: "leave", label: "Leave Records" },
          { id: "wellbeing", label: "Voluntary Self-Check" },
          { id: "support", label: "Support Requests" },
          { id: "privacy", label: "Privacy Ledger" },
        ].map((tab) => {
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-3 text-xs md:text-sm font-semibold transition-all relative whitespace-nowrap px-3 ${
                isSelected
                  ? "text-[#2C5127]"
                  : "text-[#677766] hover:text-[#182417]"
              }`}
            >
              <span>{tab.label}</span>
              {isSelected && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#2C5127] rounded-full" />
              )}
            </button>
          );
        })}
      </div>

      {/* ─── Tab Content: Dashboard / Risk ───────────────────────────── */}
      {activeTab === "dashboard" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard
              title="Operational Strain Band"
              value={
                wsiValue !== null ? (
                  <RiskBadge
                    level={riskBand}
                    score={wsiValue}
                    showScore={true}
                    size="lg"
                  />
                ) : (
                  <span className="font-mono text-xs px-2.5 py-1 rounded bg-[#EAF1E9] text-[#2C5127] font-bold border border-[#CFDDCE]">
                    {wsiStatus}
                  </span>
                )
              }
              subtitle={
                wsiValue !== null
                  ? "Partitioned: Low (0-39) / Med (40-69) / High (70-100)"
                  : "Certified operational data coverage accumulating"
              }
              icon={<Activity className="h-4 w-4" />}
              status={riskBand === "HIGH" ? "critical" : riskBand === "MEDIUM" ? "elevated" : "normal"}
            />

            <StatCard
              title="Workload vs Baseline (EWMA)"
              value={
                riskData?.current_ewma
                  ? `${riskData.current_ewma} / ${riskData?.baseline_mean || "—"} hrs`
                  : "Baseline: Pending History"
              }
              subtitle={
                riskData?.current_ewma
                  ? "Operational strain monitored"
                  : "Personal Median/MAD baseline calculation in progress"
              }
              icon={<TrendingUp className="h-4 w-4" />}
              status="normal"
            />

            <StatCard
              title="Confidential Support Requests"
              value={supportRequests.length}
              subtitle="Welfare Officer assigned"
              icon={<HeartHandshake className="h-4 w-4" />}
              status="neutral"
            />
          </div>

          {/* 14-Day Risk Score History */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-[#2C5127]" />
              <span>Personal Welfare Strain Indicator Trend</span>
            </h3>
            <div className="space-y-2">
              {riskData?.trend && riskData.trend.length > 0 ? (
                riskData.trend.map((t: any, idx: number) => (
                  <div
                    key={idx}
                    className="flex justify-between items-center p-3 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs font-mono"
                  >
                    <span className="text-[#3B4B3A]">{t.date}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-[#182417] font-bold">{t.score} pts</span>
                      <RiskBadge level={t.band} size="sm" />
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-xs text-[#677766] p-4 text-center bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                  Trend telemetry: Status {wsiStatus}. Certified multi-day snapshot window accumulating under operational scheduler.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab Content: My Profile ─────────────────────────────────── */}
      {activeTab === "profile" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Service Member Dossier
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
              <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                <span className="text-[#677766] block text-[10px] uppercase">Service Code</span>
                <span className="text-[#182417] font-bold text-sm">
                  {profile?.personnel_code || "IN-26186"}
                </span>
              </div>
              <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                <span className="text-[#677766] block text-[10px] uppercase">Pseudo ID</span>
                <span className="text-[#182417] font-bold text-sm">{profile?.pseudo_id}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                <span className="text-[#677766] block text-[10px] uppercase">Rank / Grade</span>
                <span className="text-[#182417] font-bold text-sm">{profile?.rank_or_grade}</span>
              </div>
              <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                <span className="text-[#677766] block text-[10px] uppercase">Service Years</span>
                <span className="text-[#182417] font-bold text-sm">{profile?.service_years} years</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-base font-bold text-[#182417]">Posting History</h3>
            <div className="space-y-2 text-xs">
              {profile?.postings && profile.postings.length > 0 ? (
                profile.postings.map((p: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center"
                  >
                    <div>
                      <div className="font-semibold text-[#182417]">{p.type} • {p.location}</div>
                      <div className="text-[11px] text-[#677766] font-mono">
                        {p.start_date} to {p.end_date || "Present"}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-[#677766] p-4 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                  Current unit is initial posting assignment.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab Content: Duties & Deployments ───────────────────────── */}
      {activeTab === "duties" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Operational Deployments
            </h3>
            <div className="space-y-2 text-xs">
              {deployments.length === 0 ? (
                <div className="text-[#677766] p-4 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                  No active field deployments assigned.
                </div>
              ) : (
                deployments.map((d) => (
                  <div
                    key={d.id}
                    className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center"
                  >
                    <div>
                      <div className="font-semibold text-sm text-[#182417]">
                        {d.deployment_type} ({d.location_label})
                      </div>
                      <div className="text-[11px] text-[#677766] font-mono mt-0.5">
                        {d.start_date} to {d.end_date || "Active"}
                      </div>
                    </div>
                    <span className="font-mono text-[#2C5127] font-bold px-2.5 py-1 rounded bg-[#EAF1E9] border border-[#CFDDCE]">
                      Intensity {d.intensity_level}/5
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Recent Duty Logs (Past 30 Days)
            </h3>
            <div className="space-y-2 text-xs">
              {duties.length === 0 ? (
                <div className="text-[#677766] p-4 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                  No duties logged in the past 30 days.
                </div>
              ) : (
                duties.slice(0, 10).map((d) => (
                  <div
                    key={d.id}
                    className="p-3 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center font-mono"
                  >
                    <span>
                      {d.duty_date} • {d.duty_type} ({d.shift_type})
                    </span>
                    <div className="flex items-center gap-3">
                      {d.is_night && (
                        <span className="text-[#B45309] font-bold px-2 py-0.5 rounded bg-[#FFFBEB] border border-[#FDE68A]">
                          Night Shift
                        </span>
                      )}
                      <span className="text-[#182417] font-bold">{d.hours} hrs</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Rest & Recovery Records */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Rest &amp; Recovery Records
            </h3>
            <div className="space-y-2 text-xs">
              {restRecords.length === 0 ? (
                <div className="text-[#677766] p-4 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                  No rest records logged in the past 30 days.
                </div>
              ) : (
                restRecords.slice(0, 10).map((r) => (
                  <div
                    key={r.id}
                    className="p-3 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center font-mono"
                  >
                    <span>Date: {r.date}</span>
                    <span className="text-[#15803D] font-bold px-2 py-0.5 rounded bg-[#ECFDF5] border border-[#A7F3D0]">
                      {r.rest_hours} hrs rest
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab Content: Leave ──────────────────────────────────────── */}
      {activeTab === "leave" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417]">Leave History</h3>
            <div className="space-y-2 text-xs">
              {leaves.length === 0 ? (
                <div className="text-[#677766] p-4 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                  No recorded leave history.
                </div>
              ) : (
                leaves.map((l) => (
                  <div
                    key={l.id}
                    className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center"
                  >
                    <div>
                      <div className="font-semibold text-sm text-[#182417]">
                        {l.leave_type} ({l.days} days)
                      </div>
                      <div className="text-[11px] text-[#677766] font-mono mt-0.5">
                        {l.start_date} to {l.end_date}
                      </div>
                    </div>
                    <span className="px-2.5 py-1 rounded bg-[#ECFDF5] text-[#15803D] font-mono text-[11px] font-semibold border border-[#A7F3D0]">
                      {l.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab Content: Voluntary Well-being ───────────────────────── */}
      {activeTab === "wellbeing" && (
        <div className="space-y-6">
          {/* Consent Banner */}
          <div className="p-5 rounded-2xl bg-white border border-[#CFDDCE] shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="font-serif font-bold text-base text-[#182417] flex items-center gap-2">
                <Lock className="h-4 w-4 text-[#2C5127]" />
                <span>Voluntary Confidential Self-Reflection Consent</span>
              </div>
              <p className="text-xs text-[#3B4B3A] mt-1 max-w-xl leading-relaxed">
                Participation in well-being assessments is voluntary. Raw answers are encrypted and
                strictly isolated under PostgreSQL Row-Level Security. They are never shared with
                your commander.
              </p>
            </div>
            <Button
              variant={consent?.consented ? "outline" : "primary"}
              size="sm"
              onClick={handleToggleConsent}
            >
              {consent?.consented ? "WITHDRAW CONSENT" : "GRANT ACTIVE CONSENT"}
            </Button>
          </div>

          {/* Gated Engine-B Psychometric Assessment State */}
          <div className="p-6 rounded-2xl bg-white border border-[#CFDDCE] shadow-sm space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-[#2C5127]" />
                <span>Voluntary Well-being Instrument (Engine-B)</span>
              </h3>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded-full bg-[#FFFBEB] text-[#B45309] font-bold border border-[#FDE68A]">
                INSTRUMENT_NOT_ACTIVATED
              </span>
            </div>
            
            <p className="text-xs text-[#3B4B3A] leading-relaxed">
              In strict accordance with SIH 26186 clinical safety, privacy, and non-diagnostic product rules, 
              live submission of psychometric self-check instruments is gated in production 
              (<code>ENGINE-B: INSTRUMENT_NOT_ACTIVATED, NOT_TRAINED, NOT_SHARED</code>). 
              PRAHARI does not manufacture uncertified clinical or mental health scores.
            </p>

            <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs text-[#677766] space-y-1.5 font-mono">
              <div>• Status: <strong>INSTRUMENT_NOT_ACTIVATED</strong></div>
              <div>• Clinical Boundary: No automated depression, PTSD, or psychometric diagnosis</div>
              <div>• Privacy Isolation: Raw self-check answers are never exposed to commanders or administrators</div>
              <div>• Support Channel: Use the &quot;Support Requests&quot; tab to directly and confidentially reach the Welfare Officer</div>
            </div>
          </div>

          {/* Past Submissions */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Historical Self-Reflection Log ({selfChecks.length})
            </h3>
            <div className="space-y-2 text-xs">
              {selfChecks.length === 0 ? (
                <div className="text-[#677766] p-4 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                  No historical self-checks on record.
                </div>
              ) : (
                selfChecks.map((chk) => (
                  <div
                    key={chk.id}
                    className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center font-mono"
                  >
                    <div>
                      <span className="font-bold text-[#182417]">
                        {chk.instrument_name || "Self-Reflection"}
                      </span>
                      <span className="text-[#677766] ml-2">
                        {chk.assessment_date}
                      </span>
                    </div>
                    <span className="text-[#2C5127] font-semibold px-2 py-0.5 rounded bg-[#EAF1E9] border border-[#CFDDCE]">
                      {chk.score?.items_count ? `${chk.score.items_count} items answered` : (chk.governance_status || "Recorded")}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab Content: Support Requests ──────────────────────────── */}
      {activeTab === "support" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <HeartHandshake className="h-4 w-4 text-[#2C5127]" />
              <span>Submit Confidential Welfare / Support Request</span>
            </h3>

            {supportMsg && (
              <div className="p-3.5 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] text-[#15803D] text-xs flex items-center gap-2 animate-in fade-in">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>{supportMsg}</span>
              </div>
            )}

            <form onSubmit={handleCreateSupportRequest} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#3B4B3A] mb-1.5 font-mono">
                    REQUEST TYPE
                  </label>
                  <select
                    value={supportType}
                    onChange={(e) => setSupportType(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-white border border-[#CFDDCE] rounded-lg text-xs md:text-sm text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                  >
                    <option value="LEAVE_ASSISTANCE">Leave &amp; Rest Assistance</option>
                    <option value="STRESS_FATIGUE">Operational Fatigue / Stress Support</option>
                    <option value="MEDICAL_HEALTH">Medical / Physical Well-being Consultation</option>
                    <option value="FAMILY_PERSONAL">Personal / Family Welfare Assistance</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#3B4B3A] mb-1.5 font-mono">
                    PRIORITY
                  </label>
                  <select
                    value={supportPriority}
                    onChange={(e) => setSupportPriority(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-white border border-[#CFDDCE] rounded-lg text-xs md:text-sm text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                  >
                    <option value="LOW">Low (Routine check)</option>
                    <option value="MEDIUM">Medium (Within 48 hours)</option>
                    <option value="HIGH">High (Urgent attention)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#3B4B3A] mb-1.5 font-mono">
                  REQUEST DETAILS
                </label>
                <textarea
                  rows={3}
                  value={supportDetails}
                  onChange={(e) => setSupportDetails(e.target.value)}
                  placeholder="Confidential explanation of the support requested..."
                  required
                  className="w-full px-3.5 py-2.5 bg-white border border-[#CFDDCE] rounded-lg text-xs md:text-sm text-[#182417] placeholder-[#9AA899] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <Button
                type="submit"
                disabled={submittingSupport || !supportDetails}
                loading={submittingSupport}
                icon={<Send className="h-4 w-4" />}
              >
                Submit Confidential Request
              </Button>
            </form>
          </div>

          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-base font-bold text-[#182417]">Support Request Log</h3>
            <div className="space-y-2 text-xs">
              {supportRequests.length === 0 ? (
                <div className="text-[#677766] p-4 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                  No support requests on record.
                </div>
              ) : (
                supportRequests.map((r) => (
                  <div
                    key={r.id}
                    className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center"
                  >
                    <div>
                      <div className="font-semibold text-sm text-[#182417]">
                        {r.request_type} (Priority: {r.priority})
                      </div>
                      <div className="text-[11px] text-[#677766] mt-0.5">{r.request_text}</div>
                    </div>
                    <span className="font-mono text-[#2C5127] font-bold px-2.5 py-1 rounded bg-[#EAF1E9] border border-[#CFDDCE]">
                      {r.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab Content: Privacy Ledger ────────────────────────────── */}
      {activeTab === "privacy" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <Lock className="h-4 w-4 text-[#15803D]" />
              <span>Immutable Privacy &amp; Access Log</span>
            </h3>
            <p className="text-xs text-[#3B4B3A] leading-relaxed">
              Every operation on your profile, well-being consent, and support records generates an
              immutable audit record in PostgreSQL. No unauthorized roles can access private records.
            </p>
            <div className="space-y-2 text-xs font-mono">
              {privacyHistory.length === 0 ? (
                <div className="text-[#677766] p-4 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                  No security events logged.
                </div>
              ) : (
                privacyHistory.map((p) => (
                  <div
                    key={p.id}
                    className="p-3 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center"
                  >
                    <span>
                      {p.timestamp} • {p.action}
                    </span>
                    <span className="text-[#15803D] font-bold">{p.result}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
