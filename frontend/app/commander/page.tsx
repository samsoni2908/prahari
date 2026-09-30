"use client";

import React, { useState, useEffect } from "react";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { Shell } from "@/components/layout/Shell";
import { StatCard } from "@/components/ui/StatCard";
import { Modal } from "@/components/ui/Modal";
import { RiskDistributionChart } from "@/components/charts/RiskDistributionChart";
import { WorkloadTrendChart } from "@/components/charts/WorkloadTrendChart";
import { api } from "@/lib/api";
import {
  Users,
  Shield,
  Clock,
  Calendar,
  Layers,
  MapPin,
  Lock,
  FileText,
  AlertTriangle,
  Activity,
  Download,
  ChevronRight,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { useToast } from "@/components/ui/Toast";
import { SkeletonCard, SkeletonTable } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { RiskBadge } from "@/components/ui/RiskBadge";

export default function CommanderPortal() {
  const { toast } = useToast();
  const [currentTab, setCurrentTab] = useState<string>("overview");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const tabParam = new URLSearchParams(window.location.search).get("tab");
      if (tabParam) setCurrentTab(tabParam);
    }
  }, []);

  const handleTabChange = (newTab: string) => {
    setCurrentTab(newTab);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", newTab);
      window.history.replaceState({}, "", url.toString());
    }
  };

  const [unitData, setUnitData] = useState<any>(null);
  const [unitStats, setUnitStats] = useState<any>(null);
  const [workload, setWorkload] = useState<any>(null);
  const [workloadChart, setWorkloadChart] = useState<any>(null);
  const [personnelList, setPersonnelList] = useState<any[]>([]);
  const [riskTrends, setRiskTrends] = useState<any>(null);
  const [deployments, setDeployments] = useState<any[]>([]);
  const [leaves, setLeaves] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedSoldier, setSelectedSoldier] = useState<any>(null);

  useEffect(() => {
    const loadCommanderData = async () => {
      setLoading(true);
      try {
        const [uRes, sRes, wRes, rRes, dRes, lRes, wcRes, pRes] = await Promise.allSettled([
          api.get("/commander/unit"),
          api.get("/commander/unit/stats"),
          api.get("/commander/unit/workload"),
          api.get("/commander/unit/risk-trends"),
          api.get("/commander/unit/deployments"),
          api.get("/commander/unit/leave"),
          api.get("/commander/unit/workload-chart"),
          api.get("/commander/unit/personnel"),
        ]);
        if (uRes.status === "fulfilled") setUnitData(uRes.value);
        if (sRes.status === "fulfilled") setUnitStats(sRes.value);
        if (wRes.status === "fulfilled") setWorkload(wRes.value);
        if (rRes.status === "fulfilled") setRiskTrends(rRes.value);
        if (dRes.status === "fulfilled") setDeployments(dRes.value || []);
        if (lRes.status === "fulfilled") setLeaves(lRes.value || []);
        if (wcRes.status === "fulfilled") setWorkloadChart(wcRes.value);
        if (pRes.status === "fulfilled") setPersonnelList(pRes.value || []);
      } catch (err) {
        console.error("Error loading commander dashboard", err);
      } finally {
        setLoading(false);
      }
    };
    loadCommanderData();
  }, []);

  const SectionHeader: React.FC<{ title: string; subtitle?: string; action?: React.ReactNode }> = ({ title, subtitle, action }) => (
    <div className="flex items-start justify-between mb-5">
      <div>
        <h2 className="text-lg font-bold text-prahari-textPrimary">{title}</h2>
        {subtitle && <p className="text-sm text-prahari-textMuted mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );

  const riskLow = riskTrends?.low_risk_count ?? 0;
  const riskMed = riskTrends?.medium_risk_count ?? 0;
  const riskHigh = riskTrends?.high_risk_count ?? 0;

  const [decidingLeaveId, setDecidingLeaveId] = useState<string | null>(null);

  const handleLeaveDecision = async (leaveId: string, decision: "APPROVED" | "REJECTED") => {
    setDecidingLeaveId(leaveId);
    try {
      await api.post(`/commander/unit/leave/${leaveId}/decision`, {
        decision,
        remarks: `Decision by Commander on ${new Date().toISOString().split("T")[0]}`
      });
      toast.success(`Leave request ${decision === "APPROVED" ? "approved" : "rejected"} successfully`);
      const [lRes, sRes] = await Promise.allSettled([
        api.get("/commander/unit/leave"),
        api.get("/commander/unit/stats"),
      ]);
      if (lRes.status === "fulfilled") setLeaves(lRes.value || []);
      if (sRes.status === "fulfilled") setUnitStats(sRes.value);
    } catch (err: any) {
      console.error("Leave decision error", err);
      toast.error(err?.response?.data?.detail || "Failed to record leave decision");
    } finally {
      setDecidingLeaveId(null);
    }
  };

  const pendingLeaves = leaves.filter((l: any) => l.status === "PENDING");
  const historyLeaves = leaves.filter((l: any) => l.status !== "PENDING");

  return (
    <RoleGuard allowedRoles={["COMMANDER"]}>
      <Shell currentTab={currentTab} onTabChange={handleTabChange}>

        {/* ── Overview banner ─────────────────── */}
        {(currentTab === "overview" || currentTab === "unit_overview") && (
          <div
            className="rounded-2xl p-5 text-white mb-5 shadow-card"
            style={{ background: "linear-gradient(135deg, #243D20 0%, #2E4F28 50%, #385E31 100%)" }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[#CDE0CB] mb-0.5">Command Battalion Console</p>
                <h1 className="text-xl font-bold">
                  {loading ? "Loading..." : (unitStats?.unit_name || unitData?.unit_name || "Battalion HQ")}
                </h1>
                <p className="text-sm text-[#CDE0CB]/90 mt-0.5">
                  Code: {unitStats?.unit_code || unitData?.unit_code || "—"} · Coverage: {unitStats?.coverage_ratio != null ? `${Math.round(unitStats.coverage_ratio * 100)}%` : "—"}
                </p>
              </div>
              <div
                className="hidden md:flex items-center gap-2 px-3 py-2 rounded-xl text-xs"
                style={{ background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.2)" }}
              >
                <Lock className="w-4 h-4 text-yellow-300" />
                <div>
                  <div className="text-yellow-300 font-semibold">PRIVACY FIREWALL</div>
                  <div className="text-[#CDE0CB] text-[10px]">Aggregate stats only</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Overview / Unit Overview ─────────── */}
        {(currentTab === "overview" || currentTab === "unit_overview") && (
          <div className="space-y-5 animate-fade-in">
            {/* ── Stat Cards ──────────────────────── */}
            {loading ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                {[1,2,3,4].map(i => <SkeletonCard key={i} />)}
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                <StatCard label="Total Personnel" value={unitStats?.total_personnel ?? 0} subtext={`Sanctioned: ${unitData?.sanctioned_strength || unitStats?.sanctioned_strength || "—"}`} icon={<Users style={{width:"18px",height:"18px"}}/>} accentColor="blue" />
                <StatCard label="Available Strength" value={unitStats?.available_strength ?? 0} subtext="Ready for deployment" icon={<Shield style={{width:"18px",height:"18px"}}/>} accentColor="green" trend={{ direction: "up", label: unitStats?.total_personnel ? `${Math.round(((unitStats.available_strength ?? 0) / unitStats.total_personnel) * 100)}% ready` : "—" }} />
                <StatCard label="On Leave / Rest" value={unitStats?.on_leave_count ?? 0} subtext="Rotational welfare leave" icon={<Calendar style={{width:"18px",height:"18px"}}/>} accentColor="gold" />
                <StatCard label="Fatigue / Watchlist" value={workload?.fatigue_risk_count ?? 0} subtext="High night rotation index" icon={<AlertTriangle style={{width:"18px",height:"18px"}}/>} accentColor="amber" trend={{ direction: "stable", label: "Within limits" }} />
              </div>
            )}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* Risk distribution */}
              <div className="card p-5">
                <div className="font-semibold text-prahari-textPrimary mb-1">Welfare Risk Distribution</div>
                <p className="text-xs text-prahari-textMuted mb-4">Aggregated risk assessment across the unit</p>
                <RiskDistributionChart low={riskLow} medium={riskMed} high={riskHigh} />
                <div className="grid grid-cols-3 gap-3 mt-4">
                  {[
                    { label: "Stable", count: riskLow, color: "#2E7D32", bg: "#E8F5E9" },
                    { label: "Watch", count: riskMed, color: "#F57C00", bg: "#FFF3E0" },
                    { label: "Attention", count: riskHigh, color: "#C62828", bg: "#FFEBEE" },
                  ].map(r => (
                    <div key={r.label} className="rounded-lg p-3 text-center" style={{ background: r.bg }}>
                      <div className="text-lg font-bold" style={{ color: r.color }}>{r.count}</div>
                      <div className="text-xs font-medium" style={{ color: r.color }}>{r.label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Workload */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-1">
                  <div className="font-semibold text-prahari-textPrimary">Operational Duty Workload</div>
                  <span className="text-xs text-prahari-textMuted">Weekly Aggregates</span>
                </div>
                <p className="text-xs text-prahari-textMuted mb-4">Unit-wide duty concentration and night rotation metrics</p>
                <WorkloadTrendChart
                  data={
                    (workloadChart?.trend || workloadChart?.daily_trend)?.map((d: any) => ({
                      label: d.day || d.label || d.date?.substring(5) || "Day",
                      hours: d.avg_hours_per_soldier ?? d.hours ?? 8,
                    })) || undefined
                  }
                />
                <div className="grid grid-cols-2 gap-3 mt-4">
                  <div className="rounded-lg p-3" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                    <div className="text-xs text-prahari-textMuted mb-1">AVG DUTY HOURS</div>
                    <div className="font-bold text-prahari-textPrimary">{workload?.average_weekly_duty_hours != null ? `${workload.average_weekly_duty_hours} hrs/wk` : "—"}</div>
                  </div>
                  <div className="rounded-lg p-3" style={{ background: "#FFF3E0", border: "1px solid #FFCC80" }}>
                    <div className="text-xs" style={{ color: "#F57C00" }}>NIGHT SHIFT LOAD</div>
                    <div className="font-bold" style={{ color: "#F57C00" }}>{workload?.night_shift_percentage != null ? `${workload.night_shift_percentage}%` : "—"}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Personnel tab ───────────────────── */}
        {currentTab === "personnel" && (
          <div className="animate-fade-in">
            <SectionHeader
              title="Unit Personnel Roster"
              subtitle="Individual well-being data is quarantined from command view"
              action={<span className="text-xs font-mono bg-gray-100 px-3 py-1.5 rounded-full text-prahari-textMuted">{personnelList.length} soldiers</span>}
            />
            <div className="card overflow-hidden">
              {loading ? (
                <div className="p-5"><SkeletonTable rows={5} cols={5} /></div>
              ) : personnelList.length > 0 ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Service Code</th>
                        <th>Full Name</th>
                        <th>Rank / Grade</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {personnelList.map((p) => (
                        <tr key={p.id} className="cursor-pointer" onClick={() => setSelectedSoldier(p)}>
                          <td className="font-mono font-semibold text-xs" style={{ color: "#385E31" }}>{p.personnel_code}</td>
                          <td className="font-semibold">{p.full_name}</td>
                          <td className="text-prahari-textSecondary">{p.rank_or_grade}</td>
                          <td className="text-prahari-textMuted text-xs">{p.role_title}</td>
                          <td><span className="status-stable text-xs px-2 py-0.5 rounded-full">{p.status || "Active"}</span></td>
                          <td><ChevronRight className="w-4 h-4 text-prahari-textMuted" /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-6">
                  <EmptyState icon={<Users className="w-5 h-5"/>} title="No Personnel Found" message="No personnel records in this unit." />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Deployment tab ──────────────────── */}
        {currentTab === "deployment" && (
          <div className="animate-fade-in">
            <SectionHeader title="Unit Deployments" />
            <div className="card overflow-hidden">
              {loading ? (
                <div className="p-5"><SkeletonTable rows={4} cols={4} /></div>
              ) : deployments.length > 0 ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead><tr><th>Location</th><th>Start Date</th><th>End Date</th><th>Status</th></tr></thead>
                    <tbody>
                      {deployments.map((d) => (
                        <tr key={d.id}>
                          <td className="font-medium">{d.location_label || d.deployment_type || "Operational Sector"}</td>
                          <td>{d.start_date}</td>
                          <td>{d.end_date || "Ongoing"}</td>
                          <td><span className={d.end_date ? "status-stable" : "status-low"} style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "999px", display: "inline-block" }}>{d.end_date ? "Completed" : "Active"}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-6">
                  <EmptyState icon={<MapPin className="w-5 h-5"/>} title="No Deployments" message="No operational deployments logged for this unit." />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Leave tab ───────────────────────── */}
        {currentTab === "leave" && (
          <div className="animate-fade-in space-y-6">
            <SectionHeader
              title="Unit Leave & Rest Governance"
              subtitle="Command authorization portal for rotational leave and rest schedules"
            />

            {/* Pending Leave Requests (Command Authorization) */}
            <div className="card overflow-hidden">
              <div className="p-4 border-b border-gray-100 flex items-center justify-between" style={{ background: "#FBFDFB" }}>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-600" />
                  <span className="font-semibold text-sm text-prahari-textPrimary">Pending Leave Applications</span>
                  {pendingLeaves.length > 0 && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                      {pendingLeaves.length} Action Required
                    </span>
                  )}
                </div>
                <span className="text-xs text-prahari-textMuted">Command Authorization Mandatory</span>
              </div>
              {loading ? (
                <div className="p-5"><SkeletonTable rows={2} cols={5} /></div>
              ) : pendingLeaves.length > 0 ? (
                <div className="divide-y divide-gray-100">
                  {pendingLeaves.map((l: any) => (
                    <div key={l.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/50 transition-colors">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-prahari-textPrimary">{l.full_name || "Soldier"}</span>
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                            {l.personnel_code || "—"}
                          </span>
                          <span className="text-xs text-prahari-textMuted">· {l.rank_or_grade || "Rank N/A"}</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-prahari-textSecondary">
                          <div><span className="font-medium text-slate-700">Type:</span> {l.leave_type}</div>
                          <div><span className="font-medium text-slate-700">Duration:</span> {l.start_date} to {l.end_date} {l.days_count ? `(${l.days_count} days)` : ""}</div>
                          {l.reason && <div><span className="font-medium text-slate-700">Reason:</span> <span className="italic">{l.reason}</span></div>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          disabled={decidingLeaveId === l.id}
                          onClick={() => handleLeaveDecision(l.id, "APPROVED")}
                          className="px-3.5 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm flex items-center gap-1.5 transition-all disabled:opacity-50 hover:brightness-110 active:scale-95 cursor-pointer"
                          style={{ background: "#2E7D32" }}
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          {decidingLeaveId === l.id ? "Processing..." : "Approve"}
                        </button>
                        <button
                          type="button"
                          disabled={decidingLeaveId === l.id}
                          onClick={() => handleLeaveDecision(l.id, "REJECTED")}
                          className="px-3.5 py-1.5 rounded-lg text-xs font-bold text-white shadow-sm flex items-center gap-1.5 transition-all disabled:opacity-50 hover:brightness-110 active:scale-95 cursor-pointer"
                          style={{ background: "#C62828" }}
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          {decidingLeaveId === l.id ? "Processing..." : "Reject"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6 text-center text-sm text-prahari-textMuted flex items-center justify-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  No pending leave applications. All unit leave requests are cleared.
                </div>
              )}
            </div>

            {/* Historical / Active Leave Register */}
            <div className="card overflow-hidden">
              <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                <span className="font-semibold text-sm text-prahari-textPrimary">Approved & Historical Leave Records</span>
                <span className="text-xs font-mono text-prahari-textMuted">{historyLeaves.length} records</span>
              </div>
              {loading ? (
                <div className="p-5"><SkeletonTable rows={4} cols={5} /></div>
              ) : historyLeaves.length > 0 ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Personnel</th>
                        <th>Type</th>
                        <th>Dates</th>
                        <th>Days</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historyLeaves.map((l: any) => (
                        <tr key={l.id}>
                          <td>
                            <div className="font-medium text-sm text-prahari-textPrimary">{l.full_name || "—"}</div>
                            <div className="text-xs font-mono text-prahari-textMuted">{l.personnel_code} {l.rank_or_grade ? `· ${l.rank_or_grade}` : ""}</div>
                          </td>
                          <td className="font-medium text-xs">{l.leave_type}</td>
                          <td className="text-xs whitespace-nowrap">{l.start_date} → {l.end_date}</td>
                          <td className="text-xs font-mono">{l.days_count ?? "—"}</td>
                          <td>
                            <span
                              className="text-xs font-semibold px-2.5 py-1 rounded-full inline-block whitespace-nowrap"
                              style={
                                l.status === "APPROVED"
                                  ? { background: "#E8F5E9", color: "#2E7D32", border: "1px solid #A5D6A7" }
                                  : l.status === "REJECTED"
                                  ? { background: "#FFEBEE", color: "#C62828", border: "1px solid #EF9A9A" }
                                  : { background: "#F1F5F9", color: "#475569", border: "1px solid #CBD5E1" }
                              }
                            >
                              {l.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-6">
                  <EmptyState icon={<Calendar className="w-5 h-5"/>} title="No Leave Records" message="No processed leave records found for this unit." />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Workload tab ─────────────────────── */}
        {currentTab === "workload" && (
          <div className="animate-fade-in">
            <SectionHeader title="Unit Workload Analytics" subtitle="Weekly duty concentration across the battalion" />
            <div className="card p-5">
              <WorkloadTrendChart
                data={
                  (workloadChart?.trend || workloadChart?.daily_trend)?.map((d: any) => ({
                    label: d.day || d.label || d.date?.substring(5) || "Day",
                    hours: d.avg_hours_per_soldier ?? d.hours ?? 8,
                  })) || undefined
                }
              />
            </div>
          </div>
        )}

        {/* ── Risk Trends tab ──────────────────── */}
        {currentTab === "risk_trends" && (
          <div className="animate-fade-in">
            <SectionHeader title="Risk Trends & Distribution" subtitle="Aggregate welfare risk across the unit — no individual raw data" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="card p-5">
                <div className="font-semibold text-prahari-textPrimary mb-4">Welfare Risk Distribution</div>
                <RiskDistributionChart low={riskLow} medium={riskMed} high={riskHigh} />
              </div>
              <div className="card p-5">
                <div className="font-semibold text-prahari-textPrimary mb-4">Risk Summary</div>
                <div className="space-y-3">
                  {[
                    { label: "Stable (LOW)", count: riskLow, pct: riskLow + riskMed + riskHigh > 0 ? Math.round((riskLow / (riskLow + riskMed + riskHigh)) * 100) : 0, color: "#2E7D32", bg: "#E8F5E9", border: "#A5D6A7" },
                    { label: "Watch (MEDIUM)", count: riskMed, pct: riskLow + riskMed + riskHigh > 0 ? Math.round((riskMed / (riskLow + riskMed + riskHigh)) * 100) : 0, color: "#F57C00", bg: "#FFF3E0", border: "#FFCC80" },
                    { label: "Attention (HIGH)", count: riskHigh, pct: riskLow + riskMed + riskHigh > 0 ? Math.round((riskHigh / (riskLow + riskMed + riskHigh)) * 100) : 0, color: "#C62828", bg: "#FFEBEE", border: "#EF9A9A" },
                  ].map(r => (
                    <div key={r.label} className="flex items-center justify-between p-3 rounded-xl" style={{ background: r.bg, border: `1px solid ${r.border}` }}>
                      <span className="text-sm font-semibold" style={{ color: r.color }}>{r.label}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-bold" style={{ color: r.color }}>{r.count} personnel</span>
                        <span className="text-xs" style={{ color: r.color }}>{r.pct}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Reports tab ─────────────────────── */}
        {currentTab === "reports" && (
          <div className="animate-fade-in space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-prahari-textPrimary">Unit Readiness Reports</h2>
                <p className="text-sm text-prahari-textMuted mt-0.5">Generated in compliance with welfare governance directives</p>
              </div>
              <button
                className="btn-primary text-sm py-2 px-4"
                onClick={() => {
                  const report = {
                    generated_at: new Date().toISOString(),
                    unit_code: unitStats?.unit_code || unitData?.unit_code || "—",
                    unit_name: unitStats?.unit_name || unitData?.unit_name || "—",
                    total_personnel: unitStats?.total_personnel ?? 0,
                    available_strength: unitStats?.available_strength ?? 0,
                    on_leave_count: unitStats?.on_leave_count ?? 0,
                    fatigue_risk_count: workload?.fatigue_risk_count ?? 0,
                    risk_distribution: { low: riskLow, medium: riskMed, high: riskHigh },
                  };
                  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `unit-readiness-${new Date().toISOString().slice(0, 10)}.json`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
              >
                <Download className="w-4 h-4" /> Export Report (JSON)
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="card p-5">
                <div className="font-semibold text-prahari-textPrimary mb-4 flex items-center gap-2">
                  <FileText className="w-4 h-4" style={{ color: "#385E31" }} />
                  Welfare Risk Distribution
                </div>
                <RiskDistributionChart low={riskLow} medium={riskMed} high={riskHigh} />
              </div>

              <div className="card p-5">
                <div className="font-semibold text-prahari-textPrimary mb-4 flex items-center gap-2">
                  <Shield className="w-4 h-4" style={{ color: "#F5A623" }} />
                  Unit Readiness Summary
                </div>
                <div className="space-y-3">
                  {[
                    { label: "Total Sanctioned Force", value: `${unitData?.sanctioned_strength || unitStats?.sanctioned_strength || "—"} soldiers` },
                    { label: "Available Deployment Strength", value: `${unitStats?.available_strength ?? 0} soldiers`, highlight: "#2E7D32" },
                    { label: "Active Rotational Rest", value: `${unitStats?.on_leave_count ?? 0} soldiers`, highlight: "#F57C00" },
                    { label: "Avg Weekly Shift Duration", value: workload?.average_weekly_duty_hours != null ? `${workload.average_weekly_duty_hours} hrs` : "—", highlight: "#385E31" },
                  ].map((row) => (
                    <div key={row.label} className="flex items-center justify-between p-3 rounded-lg" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                      <span className="text-sm text-prahari-textSecondary">{row.label}</span>
                      <span className="text-sm font-bold" style={{ color: row.highlight || "#243D20" }}>{row.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Settings tab ─────────────────────── */}
        {currentTab === "settings" && (
          <div className="animate-fade-in">
            <SectionHeader title="Console Governance & Privacy" subtitle="Commander scope boundaries and privacy firewall status" />
            <div className="card p-5 space-y-3">
              {[
                { title: "Privacy Firewall", desc: "Individual raw survey answers masked from command view", status: "Enforced", color: "#2E7D32", bg: "#E8F5E9", border: "#A5D6A7" },
                { title: "Scope Boundary", desc: "Battalion/Unit aggregate analytics only", status: "Active", color: "#243D20", bg: "#EFF5EE", border: "#CDE0CB" },
                { title: "Aggregation Floor", desc: "Minimum 5 personnel required for group-level statistics", status: "N≥5", color: "#F57C00", bg: "#FFF3E0", border: "#FFCC80" },
              ].map((item) => (
                <div key={item.title} className="flex items-center justify-between p-4 rounded-xl" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                  <div>
                    <div className="font-semibold text-sm text-prahari-textPrimary">{item.title}</div>
                    <div className="text-xs text-prahari-textMuted mt-0.5">{item.desc}</div>
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full shrink-0 ml-3"
                    style={{ background: item.bg, color: item.color, border: `1px solid ${item.border}` }}>
                    {item.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Soldier Modal (availability dossier) ── */}
        <Modal
          isOpen={!!selectedSoldier}
          onClose={() => setSelectedSoldier(null)}
          title={`Availability Dossier: ${selectedSoldier?.personnel_code || ""}`}
          subtitle="Read-only — individual well-being data quarantined from command view"
          maxWidth="md"
        >
          {selectedSoldier && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 rounded-xl" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                <div className="w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg shrink-0" style={{ background: "linear-gradient(135deg, #243D20, #385E31)" }}>
                  {selectedSoldier.full_name?.charAt(0)?.toUpperCase() || "P"}
                </div>
                <div>
                  <div className="font-bold text-prahari-textPrimary">{selectedSoldier.full_name}</div>
                  <div className="text-sm text-prahari-textMuted">{selectedSoldier.rank_or_grade} · {selectedSoldier.role_title}</div>
                  <div className="text-xs font-mono mt-0.5" style={{ color: "#385E31" }}>{selectedSoldier.personnel_code}</div>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                <span className="text-sm text-prahari-textSecondary">Current Status</span>
                <span className="status-stable text-xs px-2.5 py-1 rounded-full">{selectedSoldier.status || "Active"}</span>
              </div>

              <div className="flex items-start gap-2.5 p-3 rounded-lg" style={{ background: "#FFF8E1", border: "1px solid #FFCC80" }}>
                <Lock className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "#F57C00" }} />
                <p className="text-xs" style={{ color: "#795548" }}>
                  Individual well-being data and raw survey answers are quarantined from command view under Privacy Firewall.
                </p>
              </div>
            </div>
          )}
        </Modal>

      </Shell>
    </RoleGuard>
  );
}
