"use client";

import React, { useState, useEffect, useCallback } from "react";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { Shell } from "@/components/layout/Shell";
import { StatCard } from "@/components/ui/StatCard";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { Modal } from "@/components/ui/Modal";
import { RiskDistributionChart } from "@/components/charts/RiskDistributionChart";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import {
  Search, Users, AlertTriangle, HeartPulse, CheckCircle, FileText,
  Calendar, Lock, ChevronRight, ChevronLeft, X, Shield, Send, Eye, Bell, Activity,
  Filter, RefreshCw, XCircle, CheckCheck, Check, ShieldCheck, MapPin,
  Layers, FileCheck, Plus,
} from "lucide-react";
import { SkeletonCard, SkeletonTable, SkeletonProfile } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";

export default function WelfarePortal() {
  const { toast } = useToast();
  const [currentTab, setCurrentTab] = useState<string>("overview");
  const [pendingPersonnelId, setPendingPersonnelId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const sp = new URLSearchParams(window.location.search);
      const tabParam = sp.get("tab");
      const pidParam = sp.get("personnel_id");
      if (tabParam) setCurrentTab(tabParam);
      if (pidParam) setPendingPersonnelId(pidParam);
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

  // Stats
  const [stats, setStats] = useState<any>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(false);

  // Personnel search
  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Alerts
  const [alertsList, setAlertsList] = useState<any[]>([]);
  const [alertStatusFilter, setAlertStatusFilter] = useState("ALL");
  const [isLoadingAlerts, setIsLoadingAlerts] = useState(false);
  const [resolvingAlertId, setResolvingAlertId] = useState<string | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState("");

  // Actions log
  const [actionsList, setActionsList] = useState<any[]>([]);
  const [isLoadingActions, setIsLoadingActions] = useState(false);

  // Dossier
  const [selectedPersonnelId, setSelectedPersonnelId] = useState<string | null>(null);
  const [dossierTab, setDossierTab] = useState("overview");
  const [dossierData, setDossierData] = useState<any>(null);
  const [isLoadingDossier, setIsLoadingDossier] = useState(false);

  // Action Modal
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);
  const [actionPersonnelId, setActionPersonnelId] = useState("");
  const [personnelOptions, setPersonnelOptions] = useState<any[]>([]);
  const [actionType, setActionType] = useState("Welfare Follow-up");
  const [actionNotes, setActionNotes] = useState("");
  const [actionFollowUpDate, setActionFollowUpDate] = useState("");
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);

  const fetchStats = useCallback(async () => {
    setIsLoadingStats(true);
    try {
      const data = await api.get("/welfare/stats");
      setStats(data);
    } catch (err) { console.error("welfare stats error", err); }
    finally { setIsLoadingStats(false); }
  }, []);

  const fetchPersonnel = useCallback(async (q = searchQuery, filter = riskFilter) => {
    setIsSearching(true);
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.append("q", q.trim());
      if (filter !== "ALL") params.append("risk_level", filter);
      const res = await api.get(`/welfare/personnel/search?${params.toString()}`);
      setSearchResults(res || []);
      if (filter === "ALL" && !q.trim()) {
        setPersonnelOptions(res || []);
      }
    } catch (err) { console.error("personnel search error", err); }
    finally { setIsSearching(false); }
  }, [searchQuery, riskFilter]);

  const fetchAlerts = useCallback(async (status = alertStatusFilter) => {
    setIsLoadingAlerts(true);
    try {
      const params = new URLSearchParams();
      if (status !== "ALL") params.append("status_filter", status);
      const res = await api.get(`/welfare/alerts?${params.toString()}`);
      setAlertsList(res || []);
    } catch (err) { console.error("alerts error", err); }
    finally { setIsLoadingAlerts(false); }
  }, [alertStatusFilter]);

  const fetchActions = useCallback(async () => {
    setIsLoadingActions(true);
    try {
      const res = await api.get("/welfare/actions");
      setActionsList(res || []);
    } catch (err) { console.error("actions error", err); }
    finally { setIsLoadingActions(false); }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchPersonnel("", "ALL");
    fetchAlerts("ALL");
    fetchActions();
  }, []);

  useEffect(() => {
    const t = setTimeout(() => fetchPersonnel(searchQuery, riskFilter), 300);
    return () => clearTimeout(t);
  }, [searchQuery, riskFilter]);

  useEffect(() => { fetchAlerts(alertStatusFilter); }, [alertStatusFilter]);

  const handleOpenCase = async (id: string, initialTab = "overview") => {
    setSelectedPersonnelId(id);
    setDossierTab(initialTab);
    setCurrentTab("personnel");
    setIsLoadingDossier(true);
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
    try {
      const dossierRes = await api.get(`/welfare/personnel/${id}/dossier`);
      setDossierData(dossierRes);
    } catch (err) { console.error("dossier error", err); }
    finally { setIsLoadingDossier(false); }
  };

  const handleCloseCase = () => {
    setSelectedPersonnelId(null);
    setDossierData(null);
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  useEffect(() => {
    if (pendingPersonnelId) {
      handleOpenCase(pendingPersonnelId);
      setPendingPersonnelId(null);
    }
  }, [pendingPersonnelId]);

  const handleRecordAction = async (e: React.FormEvent) => {
    e.preventDefault();
    const targetId = selectedPersonnelId || actionPersonnelId;
    if (!targetId) {
      toast.error("Please select a soldier to record an action.");
      return;
    }
    setIsSubmittingAction(true);
    try {
      await api.post(`/welfare/personnel/${targetId}/actions`, {
        action_type: actionType,
        notes: actionNotes,
        follow_up_date: actionFollowUpDate || null,
      });
      toast.success(`Welfare action '${actionType}' recorded.`);
      setActionNotes("");
      setActionFollowUpDate("");
      setIsActionModalOpen(false);
      fetchStats();
      fetchActions();
      if (selectedPersonnelId === targetId) {
        handleOpenCase(targetId, dossierTab);
      }
    } catch (err: any) {
      toast.error("Error logging action: " + err.message);
    } finally { setIsSubmittingAction(false); }
  };

  const handleResolveAlert = async (alertId: string) => {
    try {
      const notes = resolutionNotes.trim() || "Resolved during welfare review";
      await api.post(`/welfare/alerts/${alertId}/resolve?notes=${encodeURIComponent(notes)}`);
      toast.success("Alert resolved.");
      setResolvingAlertId(null);
      setResolutionNotes("");
      fetchAlerts();
      fetchStats();
    } catch (err: any) {
      toast.error("Error resolving alert: " + err.message);
    }
  };

  // Helper component
  const SectionHeader: React.FC<{ title: string; subtitle?: string; action?: React.ReactNode }> = ({ title, subtitle, action }) => (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-5">
      <div className="min-w-0">
        <h2 className="text-lg font-bold text-prahari-textPrimary">{title}</h2>
        {subtitle && <p className="text-xs sm:text-sm text-prahari-textMuted mt-0.5">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );

  // Risk filter pills
  const RiskFilterPills = () => (
    <div className="flex items-center gap-1.5 flex-wrap">
      {["ALL", "HIGH", "MEDIUM", "LOW"].map((lvl) => {
        const active = riskFilter === lvl;
        const count =
          lvl === "ALL"
            ? (stats?.total_personnel_evaluated ?? searchResults.length)
            : lvl === "HIGH"
            ? (stats?.high_risk_count ?? 0)
            : lvl === "MEDIUM"
            ? (stats?.medium_risk_count ?? 0)
            : (stats?.low_risk_count ?? 0);

        const styles: Record<string, { bg: string; color: string; border: string }> = {
          HIGH: { bg: "#FFEBEE", color: "#C62828", border: "#EF9A9A" },
          MEDIUM: { bg: "#FFF3E0", color: "#F57C00", border: "#FFCC80" },
          LOW: { bg: "#E8F5E9", color: "#2E7D32", border: "#A5D6A7" },
          ALL: { bg: "#EFF5EE", color: "#243D20", border: "#CDE0CB" },
        };
        const s = styles[lvl];
        return (
          <button
            key={lvl}
            onClick={() => setRiskFilter(lvl)}
            className="text-xs font-semibold px-2.5 py-1 rounded-full transition-all flex items-center gap-1.5"
            style={{
              background: active ? s.bg : "#F7FAFC",
              color: active ? s.color : "#718096",
              border: `1px solid ${active ? s.border : "#E2E8F0"}`,
            }}
          >
            <span>{lvl}</span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full" style={{ background: active ? "rgba(0,0,0,0.08)" : "#EDF2F7" }}>
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );

  return (
    <RoleGuard allowedRoles={["WELFARE_OFFICER"]}>
      <Shell currentTab={currentTab} onTabChange={handleTabChange}>

        {/* ── Overview tab ────────────────────── */}
        {currentTab === "overview" && (
          <div className="space-y-5 animate-fade-in">
            {/* Top Banner */}
            <div
              className="rounded-2xl p-5 text-white shadow-card"
              style={{ background: "linear-gradient(135deg, #243D20 0%, #2E4F28 50%, #385E31 100%)" }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-[#CDE0CB] mb-0.5">Welfare & Risk Monitoring Console</p>
                  <h1 className="text-xl font-bold">Personnel Welfare Officer Station</h1>
                  <p className="text-sm text-[#CDE0CB]/90 mt-0.5">
                    Authorized casework · Early risk interventions · Non-clinical decision support
                  </p>
                </div>
                <div className="hidden md:flex items-center gap-2 px-3 py-2 rounded-xl text-xs" style={{ background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.2)" }}>
                  <Lock className="w-4 h-4 text-yellow-300" />
                  <div>
                    <div className="text-yellow-300 font-semibold">PRIVACY FIREWALL</div>
                    <div className="text-[#CDE0CB] text-[10px]">Authorized Scope Only</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Overview Summary Cards with interactive navigation */}
            {isLoadingStats ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[1,2,3,4].map(i => <SkeletonCard key={i}/>)}
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div
                  onClick={() => { setRiskFilter("HIGH"); handleTabChange("risk_monitor"); }}
                  className="cursor-pointer transition-transform hover:-translate-y-0.5 group"
                  title="Click to view High Risk personnel"
                >
                  <StatCard
                    label="High Risk Watchlist"
                    value={stats?.high_risk_count ?? 0}
                    subtext="Score ≥ 70 — tap to view"
                    icon={<AlertTriangle style={{width:"18px",height:"18px"}}/>}
                    accentColor="red"
                  />
                </div>
                <div
                  onClick={() => { setRiskFilter("MEDIUM"); handleTabChange("risk_monitor"); }}
                  className="cursor-pointer transition-transform hover:-translate-y-0.5 group"
                  title="Click to view Medium Risk personnel"
                >
                  <StatCard
                    label="Watch (Medium)"
                    value={stats?.medium_risk_count ?? 0}
                    subtext="Score 40–69 — tap to view"
                    icon={<Activity style={{width:"18px",height:"18px"}}/>}
                    accentColor="amber"
                  />
                </div>
                <div
                  onClick={() => handleTabChange("alerts")}
                  className="cursor-pointer transition-transform hover:-translate-y-0.5 group"
                  title="Click to view Open Alerts"
                >
                  <StatCard
                    label="Open Alerts"
                    value={stats?.open_alerts_count ?? 0}
                    subtext="Unresolved early signals"
                    icon={<Bell style={{width:"18px",height:"18px"}}/>}
                    accentColor="violet"
                  />
                </div>
                <div
                  onClick={() => handleTabChange("actions")}
                  className="cursor-pointer transition-transform hover:-translate-y-0.5 group"
                  title="Click to view Recorded Interventions"
                >
                  <StatCard
                    label="Interventions Logged"
                    value={stats?.welfare_actions_count ?? 0}
                    subtext="Human review actions"
                    icon={<CheckCircle style={{width:"18px",height:"18px"}}/>}
                    accentColor="green"
                  />
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
              {/* Left col */}
              <div className="lg:col-span-7 space-y-5">
                {/* High/Medium watchlist */}
                <div className="card p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2 font-semibold text-prahari-textPrimary">
                      <AlertTriangle className="w-4 h-4" style={{color:"#C62828"}}/>
                      Priority Watchlist — High & Medium Risk
                    </div>
                    <button onClick={() => { setRiskFilter("HIGH"); handleTabChange("risk_monitor"); }} className="text-xs font-semibold flex items-center gap-1" style={{color:"#385E31"}}>
                      View All <ChevronRight className="w-3.5 h-3.5"/>
                    </button>
                  </div>
                  {searchResults.filter(p => ["HIGH","MEDIUM"].includes(p.current_risk_level)).length > 0 ? (
                    <div className="space-y-2">
                      {searchResults.filter(p => ["HIGH","MEDIUM"].includes(p.current_risk_level)).slice(0,5).map(p => (
                        <div key={p.id} className="flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer" style={{ border: "1px solid #E2E8F0" }} onClick={() => handleOpenCase(p.id)}>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-prahari-textPrimary">{p.full_name}</span>
                              <span className="text-xs font-mono font-semibold" style={{color:"#385E31"}}>{p.personnel_code}</span>
                            </div>
                            <div className="text-xs text-prahari-textMuted mt-0.5">{p.rank_or_grade} · {p.unit_code}</div>
                          </div>
                          <div className="flex items-center gap-2">
                            <RiskBadge level={p.current_risk_level} score={p.current_risk_score} showScore size="sm"/>
                            <ChevronRight className="w-4 h-4 text-prahari-textMuted"/>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-6 text-center text-sm text-prahari-textMuted">No high or medium risk personnel detected.</div>
                  )}
                </div>

                {/* Recent open alerts */}
                <div className="card p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2 font-semibold text-prahari-textPrimary">
                      <Bell className="w-4 h-4" style={{color:"#F57C00"}}/>
                      Active Risk Alerts
                    </div>
                    <button onClick={() => handleTabChange("alerts")} className="text-xs font-semibold flex items-center gap-1" style={{color:"#385E31"}}>
                      Manage All <ChevronRight className="w-3.5 h-3.5"/>
                    </button>
                  </div>
                  {alertsList.filter(a => a.status === "OPEN" || a.status === "UNDER_REVIEW").length > 0 ? (
                    <div className="space-y-2">
                      {alertsList.filter(a => ["OPEN","UNDER_REVIEW"].includes(a.status)).slice(0,4).map(alert => (
                        <div key={alert.id} className="flex items-start justify-between p-3 rounded-xl" style={{ border: "1px solid #E2E8F0" }}>
                          <div className="flex-1 min-w-0 mr-3">
                            <div className="flex items-center gap-2 mb-0.5">
                              <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{
                                background: alert.severity === "HIGH" ? "#FFEBEE" : "#FFF3E0",
                                color: alert.severity === "HIGH" ? "#C62828" : "#F57C00",
                              }}>{alert.severity}</span>
                              <span className="text-sm font-semibold text-prahari-textPrimary truncate">{alert.alert_type}</span>
                            </div>
                            <p className="text-xs text-prahari-textMuted truncate">{alert.message}</p>
                          </div>
                          {alert.personnel_id && (
                            <button onClick={() => handleOpenCase(alert.personnel_id, "risk")} className="btn-secondary text-xs py-1 px-2.5 shrink-0">
                              <Eye className="w-3.5 h-3.5"/> Inspect
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-6 text-center text-sm text-prahari-textMuted">All risk alerts have been resolved.</div>
                  )}
                </div>
              </div>

              {/* Right col */}
              <div className="lg:col-span-5 space-y-5">
                <div className="card p-5">
                  <div className="font-semibold text-prahari-textPrimary mb-4 flex items-center gap-2">
                    <Activity className="w-4 h-4" style={{color:"#6A1B9A"}}/>
                    Station Risk Distribution
                  </div>
                  <RiskDistributionChart
                    low={stats?.low_risk_count ?? 0}
                    medium={stats?.medium_risk_count ?? 0}
                    high={stats?.high_risk_count ?? 0}
                  />
                  <div className="text-center text-xs text-prahari-textMuted mt-2">
                    Evaluated: <strong>{stats?.total_personnel_evaluated ?? 0}</strong> personnel
                  </div>
                </div>

                <div className="card p-5">
                  <div className="font-semibold text-prahari-textPrimary mb-3 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4" style={{color:"#6A1B9A"}}/>
                    Welfare Operating Charter
                  </div>
                  <div className="space-y-2.5">
                    {[
                      "Voluntary assessments remain strictly private — raw responses isolated",
                      "Every welfare intervention requires officer sign-off in the audit register",
                      "No automatic high-stakes decisions — human review stays in the loop",
                    ].map((rule, i) => (
                      <div key={i} className="flex items-start gap-2.5">
                        <Check className="w-4 h-4 shrink-0 mt-0.5" style={{color:"#2E7D32"}}/>
                        <span className="text-xs text-prahari-textSecondary">{rule}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Search & Personnel tabs ──────────── */}
        {(currentTab === "search" || currentTab === "personnel") && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 animate-fade-in">
            {/* Directory pane */}
            <div className={selectedPersonnelId ? "hidden lg:block lg:col-span-5" : "col-span-12"}>
              <div className="card p-5">
                <div className="flex items-center justify-between mb-4">
                  <div className="font-semibold text-prahari-textPrimary flex items-center gap-2">
                    <Search className="w-4 h-4" style={{color:"#385E31"}}/>
                    Personnel Risk Directory
                  </div>
                  <RiskFilterPills />
                </div>

                {/* Search bar */}
                <div className="relative mb-4">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                    <Search className="w-4 h-4 text-prahari-textMuted"/>
                  </div>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search by Name, Service Code, or Unit..."
                    className="form-input pl-10"
                  />
                </div>

                {/* Results */}
                <div className="overflow-x-auto">
                  {isSearching ? (
                    <SkeletonTable rows={4} cols={3}/>
                  ) : searchResults.length > 0 ? (
                    <table className="data-table">
                      <thead>
                        <tr><th>Name / Code</th><th>Unit</th><th>Risk</th><th></th></tr>
                      </thead>
                      <tbody>
                        {searchResults.map(p => {
                          const isSelected = selectedPersonnelId === p.id;
                          return (
                            <tr
                              key={p.id}
                              className="cursor-pointer"
                              style={{ background: isSelected ? "#EFF5EE" : undefined }}
                              onClick={() => handleOpenCase(p.id)}
                            >
                              <td>
                                <div className="font-semibold text-prahari-textPrimary text-sm">{p.full_name}</div>
                                <div className="text-xs font-mono font-semibold" style={{color:"#385E31"}}>{p.personnel_code}</div>
                              </td>
                              <td className="text-prahari-textMuted text-xs">{p.unit_code || "—"}</td>
                              <td><RiskBadge level={p.current_risk_level} score={p.current_risk_score} showScore size="sm"/></td>
                              <td><ChevronRight className="w-4 h-4 text-prahari-textMuted"/></td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  ) : (
                    <EmptyState icon={<Search className="w-5 h-5"/>} title="No Results" message={searchQuery ? "No personnel match your search." : "Start typing to search personnel."}/>
                  )}
                </div>
              </div>
            </div>

            {/* Dossier pane */}
            {selectedPersonnelId && (
              <div id="welfare-dossier-view" className="col-span-12 lg:col-span-7 animate-slide-up">
                {isLoadingDossier ? (
                  <SkeletonProfile/>
                ) : dossierData ? (
                  <div className="card overflow-hidden">
                    {/* Dossier header */}
                    <div className="p-5" style={{ background: "linear-gradient(135deg, #4A148C, #6A1B9A)", color: "#fff" }}>
                      {/* Mobile back navigation */}
                      <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/20 lg:hidden">
                        <button
                          onClick={handleCloseCase}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white text-xs font-semibold transition-colors"
                        >
                          <ChevronLeft className="w-4 h-4" /> Back to Directory
                        </button>
                        <button
                          onClick={handleCloseCase}
                          className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white"
                          title="Close Dossier"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-full flex items-center justify-center text-white text-lg font-bold shrink-0" style={{ background: "rgba(255,255,255,0.18)" }}>
                          {dossierData.profile?.full_name?.charAt(0)?.toUpperCase() || "P"}
                        </div>
                        <div>
                          <div className="font-bold text-lg">{dossierData.profile?.full_name || "—"}</div>
                          <div className="text-sm text-purple-200">{dossierData.profile?.rank_or_grade} · {dossierData.profile?.personnel_code}</div>
                          <div className="mt-1.5">
                            <RiskBadge level={dossierData.risk?.risk_level} score={dossierData.risk?.risk_score} showScore size="md"/>
                          </div>
                        </div>
                        <div className="ml-auto flex items-center gap-2">
                          <button
                            className="btn-primary text-xs py-1.5 px-3"
                            style={{ background: "rgba(255,255,255,0.15)", border: "1px solid rgba(255,255,255,0.30)", color: "#fff" }}
                            onClick={() => setIsActionModalOpen(true)}
                          >
                            <FileCheck className="w-3.5 h-3.5"/> Record Action
                          </button>
                          <button
                            onClick={handleCloseCase}
                            className="hidden lg:flex p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors"
                            title="Close Dossier"
                          >
                            <X className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Dossier tabs */}
                    <div className="overflow-x-auto -mx-px" style={{ borderBottom: "1px solid #E2E8F0" }}>
                      <div className="flex min-w-max">
                        {["overview","risk","wellbeing","leave","deployment","service","training"].map(tab => (
                          <button
                            key={tab}
                            onClick={() => setDossierTab(tab)}
                            className="px-3 py-2.5 text-xs font-medium capitalize transition-all whitespace-nowrap"
                            style={{
                              color: dossierTab === tab ? "#6A1B9A" : "#718096",
                              borderBottom: dossierTab === tab ? "2px solid #6A1B9A" : "2px solid transparent",
                              background: "transparent",
                            }}
                          >
                            {tab === "wellbeing" ? "Well-being" : tab === "service" ? "Service" : tab}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Dossier tab content */}
                    <div className="p-5">
                      {/* Overview */}
                      {dossierTab === "overview" && (
                        <div className="space-y-4 animate-fade-in">
                          <div className="grid grid-cols-2 gap-3">
                            {[
                              { label: "Full Name", value: dossierData.profile?.full_name },
                              { label: "Personnel Code", value: dossierData.profile?.personnel_code, mono: true },
                              { label: "Rank", value: dossierData.profile?.rank_or_grade },
                              { label: "Role Title", value: dossierData.profile?.role_title },
                              { label: "Gender", value: dossierData.profile?.gender },
                              { label: "Service Category", value: dossierData.profile?.service_category },
                            ].map(f => (
                              <div key={f.label} className="rounded-lg p-3" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                                <div className="text-[10px] font-semibold uppercase tracking-wider text-prahari-textMuted mb-1">{f.label}</div>
                                <div className={`text-sm font-medium text-prahari-textPrimary ${f.mono ? "font-mono" : ""}`}>{f.value || "—"}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Risk */}
                      {dossierTab === "risk" && (
                        <div className="space-y-4 animate-fade-in">
                          <div className="flex items-center gap-4 p-4 rounded-xl" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                            <div className="text-center">
                              <div className="text-3xl font-extrabold text-prahari-textPrimary">{Math.round(dossierData.risk?.risk_score ?? 0)}</div>
                              <div className="text-xs text-prahari-textMuted">/ 100</div>
                            </div>
                            <div className="flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <RiskBadge level={dossierData.risk?.risk_level} score={dossierData.risk?.risk_score} showScore size="lg"/>
                                {dossierData.risk?.confidence_score !== undefined && dossierData.risk?.confidence_score !== null && (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                                    Confidence: {dossierData.risk.confidence_score}%
                                  </span>
                                )}
                                {dossierData.risk?.flagged_since && dossierData.risk?.risk_level === "HIGH" && (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-50 text-red-700 border border-red-200">
                                    Flagged: {dossierData.risk.flagged_since}
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-prahari-textMuted mt-1">Model: {dossierData.risk?.model_version || "baseline"} · {dossierData.risk?.prediction_date}</div>
                            </div>
                          </div>
                          {dossierData.risk?.what_changed?.length > 0 && (
                            <div className="mb-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
                              <div className="text-xs font-bold text-prahari-textPrimary mb-1.5 flex items-center justify-between">
                                <span>Recent Trajectory Shift (Since Last Week)</span>
                                <span className="text-[10px] text-prahari-textMuted">7d Delta</span>
                              </div>
                              <div className="flex flex-wrap gap-2">
                                {dossierData.risk.what_changed.map((ch: any, idx: number) => (
                                  <span key={idx} className={`text-xs px-2 py-1 rounded font-medium ${
                                    ch.impact === "INCREASING_RISK" ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-900"
                                  }`}>
                                    {ch.factor}: <strong>{ch.change_text}</strong> ({ch.direction === "UP" ? "↑" : "↓"})
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          {dossierData.risk?.contributing_factors?.length > 0 && (
                            <div>
                              <div className="font-semibold text-sm text-prahari-textPrimary mb-2">Contributing Factors</div>
                              {dossierData.risk.contributing_factors.map((f: any, i: number) => {
                                const factorText = typeof f === "string" ? f : (f?.factor || f?.human_label || JSON.stringify(f));
                                return (
                                  <div key={i} className="flex items-center gap-2 py-1.5 text-sm text-prahari-textSecondary">
                                    <CheckCircle className="w-3.5 h-3.5 shrink-0" style={{color:"#2E7D32"}}/> {factorText}
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Wellbeing */}
                      {dossierTab === "wellbeing" && (
                        <div className="animate-fade-in">
                          <div className="rounded-xl p-3 mb-4 flex items-start gap-2" style={{ background: "#E3F0FC", border: "1px solid #BFDBFE" }}>
                            <Lock className="w-4 h-4 shrink-0 mt-0.5 text-prahari-blue" />
                            <p className="text-xs text-prahari-blue">
                              Welfare Officers see authorized trend summaries only — raw questionnaire answers remain Personnel-private.
                            </p>
                          </div>
                          {((dossierData.wellbeing_assessments?.length > 0) || (dossierData.wellbeing_results?.length > 0)) ? (
                            <div className="space-y-2">
                              {(dossierData.wellbeing_assessments || dossierData.wellbeing_results).map((r: any) => (
                                <div key={r.id} className="flex items-center justify-between p-3.5 rounded-xl hover:bg-gray-50 transition-colors" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                                  <div>
                                    <div className="text-sm font-semibold text-prahari-textPrimary">{r.instrument_name || "Voluntary Well-being Check-in"}</div>
                                    <div className="text-xs text-prahari-textMuted mt-0.5">Recorded: {r.assessment_date}</div>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-xs px-2.5 py-1 rounded-full font-semibold" style={{ background: "#E8F5E9", color: "#2E7D32", border: "1px solid #A5D6A7" }}>
                                      {r.category_label?.replace("_", " ") || "Satisfactory"}
                                    </span>
                                    {r.trend_label && (
                                      <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-blue-50 text-blue-700 border border-blue-200">
                                        {r.trend_label}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <EmptyState icon={<HeartPulse className="w-5 h-5"/>} title="No Assessments" message="No well-being assessments recorded for this personnel."/>
                          )}
                        </div>
                      )}

                      {/* Leave */}
                      {dossierTab === "leave" && (
                        <div className="animate-fade-in">
                          {dossierData.leave_records?.length > 0 ? (
                            <div className="table-responsive">
                              <table className="data-table">
                                <thead><tr><th>Type</th><th>Start</th><th>End</th><th>Status</th></tr></thead>
                                <tbody>
                                  {dossierData.leave_records.map((l: any) => (
                                    <tr key={l.id}>
                                      <td className="font-medium">{l.leave_type}</td>
                                      <td className="whitespace-nowrap">{l.start_date}</td>
                                      <td className="whitespace-nowrap">{l.end_date}</td>
                                      <td><span className="status-stable text-xs px-2 py-0.5 rounded-full whitespace-nowrap">{l.status}</span></td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <EmptyState icon={<Calendar className="w-5 h-5"/>} title="No Leave Records" message="No leave records found for this personnel."/>
                          )}
                        </div>
                      )}

                      {/* Deployment */}
                      {dossierTab === "deployment" && (
                        <div className="animate-fade-in">
                          {dossierData.deployments?.length > 0 ? (
                            <div className="table-responsive">
                              <table className="data-table">
                                <thead><tr><th>Location</th><th>Start</th><th>End</th><th>Status</th></tr></thead>
                                <tbody>
                                  {dossierData.deployments.map((d: any) => (
                                    <tr key={d.id}>
                                      <td className="font-medium">{d.location_label || d.deployment_type || "—"}</td>
                                      <td className="whitespace-nowrap">{d.start_date}</td>
                                      <td className="whitespace-nowrap">{d.end_date || "Ongoing"}</td>
                                      <td><span className={d.end_date ? "status-stable" : "status-low"} style={{ fontSize:"11px", padding:"2px 8px", borderRadius:"999px", display:"inline-block", whiteSpace:"nowrap" }}>{d.end_date ? "Completed" : "Active"}</span></td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <EmptyState icon={<MapPin className="w-5 h-5"/>} title="No Deployments" message="No deployment records found."/>
                          )}
                        </div>
                      )}

                      {/* Service */}
                      {dossierTab === "service" && (
                        <div className="animate-fade-in space-y-3">
                          {[
                            { label: "Date of Joining", value: dossierData.profile?.date_of_joining },
                            { label: "Service Category", value: dossierData.profile?.service_category },
                            { label: "Current Unit", value: dossierData.profile?.unit_name },
                          ].map(f => (
                            <div key={f.label} className="flex items-center justify-between p-3 rounded-lg" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                              <span className="text-xs text-prahari-textMuted">{f.label}</span>
                              <span className="text-sm font-semibold text-prahari-textPrimary">{f.value || "—"}</span>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Training */}
                      {dossierTab === "training" && (
                        <div className="animate-fade-in">
                          {dossierData.trainings?.length > 0 ? (
                            <div className="table-responsive">
                              <table className="data-table">
                                <thead><tr><th>Training</th><th>Start</th><th>End</th><th>Status</th></tr></thead>
                                <tbody>
                                  {dossierData.trainings.map((t: any) => (
                                    <tr key={t.id}>
                                      <td className="font-medium">{t.training_name || t.training_type}</td>
                                      <td className="whitespace-nowrap">{t.start_date}</td>
                                      <td className="whitespace-nowrap">{t.end_date || "Ongoing"}</td>
                                      <td><span className="status-stable text-xs px-2 py-0.5 rounded-full whitespace-nowrap">{t.status || "Completed"}</span></td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <EmptyState icon={<Shield className="w-5 h-5"/>} title="No Training Records" message="No training records found."/>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <EmptyState icon={<Users className="w-5 h-5"/>} title="Select a personnel record" message="Click on a row in the search results to open the welfare dossier."/>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Risk Monitor tab ─────────────────── */}
        {currentTab === "risk_monitor" && (
          <div className="animate-fade-in">
            <SectionHeader
              title="Risk Monitor"
              subtitle="All evaluated personnel sorted by risk level"
              action={<RiskFilterPills/>}
            />
            <div className="card overflow-hidden">
              {isSearching ? (
                <div className="p-5"><SkeletonTable rows={5} cols={4}/></div>
              ) : searchResults.length > 0 ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead><tr><th>Name</th><th>Service Code</th><th>Unit</th><th>Risk Level</th><th></th></tr></thead>
                    <tbody>
                      {searchResults.map(p => (
                        <tr key={p.id} className="cursor-pointer" onClick={() => handleOpenCase(p.id)}>
                          <td>
                            <div className="font-semibold text-sm">{p.full_name}</div>
                            <div className="text-xs text-prahari-textMuted">{p.rank_or_grade}</div>
                          </td>
                          <td className="font-mono text-xs font-semibold" style={{color:"#385E31"}}>{p.personnel_code}</td>
                          <td className="text-prahari-textMuted text-xs">{p.unit_code}</td>
                          <td><RiskBadge level={p.current_risk_level} score={p.current_risk_score} showScore size="sm"/></td>
                          <td><button className="text-xs btn-secondary py-1 px-2.5 whitespace-nowrap" onClick={e=>{e.stopPropagation();handleOpenCase(p.id)}}><Eye className="w-3.5 h-3.5"/>View</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-6"><EmptyState icon={<AlertTriangle className="w-5 h-5"/>} title="No Personnel Found" message="No personnel match the current filter."/></div>
              )}
            </div>
          </div>
        )}

        {/* ── Assessments tab ──────────────────── */}
        {currentTab === "assessments" && (
          <div className="animate-fade-in">
            <SectionHeader title="Well-being Assessments" subtitle="Authorized summaries — raw answers remain Personnel-private" />
            <div className="card overflow-hidden">
              <div className="p-4 flex items-start gap-3 border-b border-[#CDE0CB]" style={{ background: "#EFF5EE" }}>
                <Lock className="w-4 h-4 shrink-0 mt-0.5 text-prahari-olive" />
                <p className="text-xs text-prahari-oliveDark font-medium">
                  Welfare Officers see category labels and trend only. Raw responses are locked to individual personnel under Privacy Firewall.
                </p>
              </div>
              {isSearching ? (
                <div className="p-5"><SkeletonTable rows={4} cols={5}/></div>
              ) : searchResults.length > 0 ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead><tr><th>Personnel</th><th>Latest Assessment</th><th>Wellbeing Status</th><th>Trend</th><th>Risk Level</th></tr></thead>
                    <tbody>
                      {searchResults.map(p => (
                        <tr key={p.id} className="cursor-pointer" onClick={() => handleOpenCase(p.id, "wellbeing")}>
                          <td>
                            <div className="font-semibold text-sm text-prahari-textPrimary">{p.full_name}</div>
                            <div className="text-xs font-mono text-prahari-olive font-semibold">{p.personnel_code} · {p.rank_or_grade}</div>
                          </td>
                          <td className="text-prahari-textMuted text-xs">{p.latest_assessment_date || "Routine Review"}</td>
                          <td>
                            <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                              p.latest_wellbeing_category === "ELEVATED_STRESS" ? "bg-red-50 text-red-700 border border-red-200" :
                              p.latest_wellbeing_category === "MODERATE_STRESS" ? "bg-amber-50 text-amber-700 border border-amber-200" :
                              "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            }`}>
                              {p.latest_wellbeing_category?.replace("_", " ") || "Satisfactory"}
                            </span>
                          </td>
                          <td>
                            {p.wellbeing_trend === "IMPROVING" ? <span className="status-stable text-xs px-2 py-0.5 rounded-full">Improving</span> :
                             p.wellbeing_trend === "DECLINING" || p.wellbeing_trend === "WORSENING" ? <span className="status-attention text-xs px-2 py-0.5 rounded-full">Declining</span> :
                             <span className="text-xs text-prahari-textMuted">Stable</span>}
                          </td>
                          <td><RiskBadge level={p.current_risk_level} size="sm"/></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-6"><EmptyState icon={<HeartPulse className="w-5 h-5"/>} title="No Assessment Data" message="No personnel records found for the selected criteria."/></div>
              )}
            </div>
          </div>
        )}

        {/* ── Alerts tab ───────────────────────── */}
        {currentTab === "alerts" && (
          <div className="animate-fade-in">
            <SectionHeader
              title="Risk Alerts"
              subtitle="Early welfare risk signals requiring officer review"
              action={
                <div className="flex items-center gap-2 flex-wrap">
                  {["ALL","OPEN","UNDER_REVIEW","RESOLVED"].map(s => (
                    <button key={s} onClick={() => setAlertStatusFilter(s)}
                      className="text-xs font-semibold px-2.5 py-1 rounded-full transition-all"
                      style={{
                        background: alertStatusFilter === s ? "#EFF5EE" : "#F7FAFC",
                        color: alertStatusFilter === s ? "#243D20" : "#718096",
                        border: `1px solid ${alertStatusFilter === s ? "#CDE0CB" : "#E2E8F0"}`,
                      }}>
                      {s.replace("_"," ")}
                    </button>
                  ))}
                  <button onClick={() => fetchAlerts(alertStatusFilter)} className="btn-secondary text-xs py-1 px-2.5">
                    <RefreshCw className="w-3.5 h-3.5"/>
                  </button>
                </div>
              }
            />
            <div className="card overflow-hidden">
              {isLoadingAlerts ? (
                <div className="p-5"><SkeletonTable rows={4} cols={5}/></div>
              ) : alertsList.length > 0 ? (
                <div className="divide-y" style={{borderColor:"#F0F4F8"}}>
                  {alertsList.map(alert => (
                    <div key={alert.id} className="p-4 hover:bg-gray-50 transition-colors">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="text-xs font-bold px-2 py-0.5 rounded-full whitespace-nowrap" style={{
                              background: alert.severity==="HIGH"?"#FFEBEE":alert.severity==="MEDIUM"?"#FFF3E0":"#E8F5E9",
                              color: alert.severity==="HIGH"?"#C62828":alert.severity==="MEDIUM"?"#F57C00":"#2E7D32",
                            }}>{alert.severity}</span>
                            <span className="text-sm font-semibold text-prahari-textPrimary">{alert.alert_type}</span>
                            <span className="text-xs text-prahari-textMuted">· {alert.personnel_code || alert.unit_code}</span>
                          </div>
                          <p className="text-xs text-prahari-textSecondary">{alert.message}</p>
                          <div className="text-xs text-prahari-textMuted mt-1">{alert.created_at}</div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0 flex-wrap">
                          {alert.status !== "RESOLVED" && (
                            <>
                              {alert.personnel_id && (
                                <button onClick={() => handleOpenCase(alert.personnel_id, "risk")} className="btn-secondary text-xs py-1 px-2.5">
                                  <Eye className="w-3.5 h-3.5"/> Inspect
                                </button>
                              )}
                              {resolvingAlertId === alert.id ? (
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <input
                                    type="text"
                                    value={resolutionNotes}
                                    onChange={e=>setResolutionNotes(e.target.value)}
                                    placeholder="Resolution notes..."
                                    className="form-input text-xs py-1 w-full sm:w-40"
                                  />
                                  <div className="flex gap-1.5">
                                    <button onClick={() => handleResolveAlert(alert.id)} className="btn-primary text-xs py-1 px-2.5">
                                      <Check className="w-3.5 h-3.5"/>
                                    </button>
                                    <button onClick={() => setResolvingAlertId(null)} className="btn-secondary text-xs py-1 px-2.5">
                                      <XCircle className="w-3.5 h-3.5"/>
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <button onClick={() => setResolvingAlertId(alert.id)} className="btn-primary text-xs py-1 px-2.5">
                                  <CheckCheck className="w-3.5 h-3.5"/> Resolve
                                </button>
                              )}
                            </>
                          )}
                          {alert.status === "RESOLVED" && (
                            <span className="status-stable text-xs px-2.5 py-1 rounded-full">Resolved</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-6"><EmptyState icon={<Bell className="w-5 h-5"/>} title="No Alerts" message="No alerts match the current filter."/></div>
              )}
            </div>
          </div>
        )}

        {/* ── Actions tab ──────────────────────── */}
        {currentTab === "actions" && (
          <div className="animate-fade-in space-y-5">
            <SectionHeader
              title="Welfare Actions & Interventions"
              subtitle="Record, initiate and track human welfare casework decisions"
              action={
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setActionPersonnelId(selectedPersonnelId || "");
                      setActionType("Welfare Follow-up");
                      setIsActionModalOpen(true);
                    }}
                    className="btn-primary text-xs py-2 px-3 flex items-center gap-1.5"
                  >
                    <Plus className="w-3.5 h-3.5"/> Initiate Action
                  </button>
                  <button onClick={fetchActions} className="btn-secondary text-xs py-2 px-3">
                    <RefreshCw className="w-3.5 h-3.5"/> Refresh
                  </button>
                </div>
              }
            />

            {/* Quick Intervention Desk */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                {
                  title: "Welfare Interview",
                  desc: "Conduct confidential one-on-one session",
                  type: "Contact Personnel",
                  color: "#1E88E5",
                  bg: "#E3F2FD",
                  border: "#90CAF9"
                },
                {
                  title: "Rotation / Rest",
                  desc: "Recommend rest turnaround adjustment",
                  type: "Welfare Follow-up",
                  color: "#F57C00",
                  bg: "#FFF3E0",
                  border: "#FFCC80"
                },
                {
                  title: "Support Referral",
                  desc: "Connect to psychological / family aid",
                  type: "Welfare Follow-up",
                  color: "#6A1B9A",
                  bg: "#F3E5F5",
                  border: "#CE93D8"
                },
                {
                  title: "Record Outcome",
                  desc: "Document intervention resolution",
                  type: "Record Outcome",
                  color: "#2E7D32",
                  bg: "#E8F5E9",
                  border: "#A5D6A7"
                }
              ].map((card, idx) => (
                <div
                  key={idx}
                  onClick={() => {
                    setActionPersonnelId(selectedPersonnelId || "");
                    setActionType(card.type);
                    setIsActionModalOpen(true);
                  }}
                  className="rounded-xl p-4 cursor-pointer transition-all hover:-translate-y-0.5 shadow-sm"
                  style={{ background: card.bg, border: `1px solid ${card.border}` }}
                >
                  <div className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: card.color }}>
                    {card.title}
                  </div>
                  <p className="text-xs text-prahari-textSecondary mb-3">
                    {card.desc}
                  </p>
                  <div className="flex items-center gap-1 text-xs font-semibold" style={{ color: card.color }}>
                    <span>Launch</span> <ChevronRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              ))}
            </div>

            {/* Past Casework Register */}
            <div className="card overflow-hidden">
              <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                <span className="font-semibold text-sm text-prahari-textPrimary">Immutable Welfare Action Log</span>
                <span className="text-xs font-mono text-prahari-textMuted">{actionsList.length} recorded</span>
              </div>
              {isLoadingActions ? (
                <div className="p-5"><SkeletonTable rows={4} cols={4}/></div>
              ) : actionsList.length > 0 ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead><tr><th>Action Type</th><th>Personnel</th><th>Recorded By</th><th>Date</th><th>Notes</th></tr></thead>
                    <tbody>
                      {actionsList.map((a, i) => (
                        <tr key={a.id || i}>
                          <td><span className="text-xs font-semibold px-2.5 py-1 rounded-full whitespace-nowrap" style={{background:"#F3E5F5",color:"#6A1B9A",border:"1px solid #CE93D8"}}>{a.action_type}</span></td>
                          <td>
                            <div className="font-medium text-sm">{a.personnel_name || "—"}</div>
                            <div className="text-xs font-mono text-prahari-textMuted">{a.personnel_code}</div>
                          </td>
                          <td className="text-prahari-textMuted text-xs whitespace-nowrap">{a.officer_name || "Welfare Officer"}</td>
                          <td className="text-prahari-textMuted text-xs whitespace-nowrap">{a.recorded_at || a.created_at}</td>
                          <td className="text-prahari-textSecondary text-xs max-w-[160px] truncate">{a.notes || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-6"><EmptyState icon={<FileCheck className="w-5 h-5"/>} title="No Actions Logged" message="No welfare intervention actions have been recorded yet."/></div>
              )}
            </div>
          </div>
        )}

        {/* ── Reports tab ──────────────────────── */}
        {currentTab === "reports" && (
          <div className="animate-fade-in space-y-5">
            <SectionHeader title="Welfare Reports" subtitle="Station welfare activity summaries" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="card p-5">
                <div className="font-semibold text-prahari-textPrimary mb-4 flex items-center gap-2">
                  <Activity className="w-4 h-4" style={{color:"#6A1B9A"}}/>
                  Risk Distribution
                </div>
                <RiskDistributionChart low={stats?.low_risk_count??0} medium={stats?.medium_risk_count??0} high={stats?.high_risk_count??0}/>
              </div>
              <div className="card p-5">
                <div className="font-semibold text-prahari-textPrimary mb-4 flex items-center gap-2">
                  <FileText className="w-4 h-4" style={{color:"#385E31"}}/>
                  Station Summary
                </div>
                <div className="space-y-3">
                  {[
                    { label: "Total Personnel Evaluated", value: stats?.total_personnel_evaluated ?? 0 },
                    { label: "High Risk (Attention)", value: stats?.high_risk_count ?? 0, color: "#C62828" },
                    { label: "Watch (Medium Risk)", value: stats?.medium_risk_count ?? 0, color: "#F57C00" },
                    { label: "Stable (Low Risk)", value: stats?.low_risk_count ?? 0, color: "#2E7D32" },
                    { label: "Open Alerts", value: stats?.open_alerts_count ?? 0 },
                    { label: "Interventions Recorded", value: stats?.welfare_actions_count ?? 0 },
                  ].map(row => (
                    <div key={row.label} className="flex items-center justify-between p-3 rounded-lg" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                      <span className="text-sm text-prahari-textSecondary">{row.label}</span>
                      <span className="text-sm font-bold" style={{ color: row.color || "#243D20" }}>{row.value}</span>
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
            <SectionHeader title="Welfare Officer Governance" subtitle="Authorization scope and privacy boundary settings" />
            <div className="card p-5 space-y-3">
              {[
                { title: "Authorization Scope", desc: "Individual personnel within assigned unit boundary", status: "Active", color: "#6A1B9A", bg: "#F3E5F5", border: "#CE93D8" },
                { title: "Raw Answer Access", desc: "Raw questionnaire answers permanently isolated from welfare officer view", status: "Quarantined", color: "#C62828", bg: "#FFEBEE", border: "#EF9A9A" },
                { title: "Welfare Action Audit", desc: "All interventions logged to immutable audit register", status: "Enforced", color: "#2E7D32", bg: "#E8F5E9", border: "#A5D6A7" },
                { title: "Automated Decisions", desc: "No automated high-stakes decisions — officer review mandatory", status: "Prohibited", color: "#F57C00", bg: "#FFF3E0", border: "#FFCC80" },
              ].map(item => (
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

        {/* ── Welfare Action Modal ─────────────── */}
        <Modal
          isOpen={isActionModalOpen}
          onClose={() => setIsActionModalOpen(false)}
          title="Record Welfare Action"
          subtitle="Logged to immutable audit register"
          maxWidth="md"
        >
          <form onSubmit={handleRecordAction} className="space-y-4">
            {selectedPersonnelId ? (
              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs">
                <span className="font-semibold text-emerald-800">Target Personnel: </span>
                <span className="text-emerald-700">
                  {dossierData?.profile?.full_name || "Assigned Soldier"} ({dossierData?.profile?.personnel_code || selectedPersonnelId.slice(0, 8)})
                </span>
              </div>
            ) : (
              <div>
                <label className="form-label">Select Soldier / Personnel <span className="text-red-500">*</span></label>
                <select
                  value={actionPersonnelId}
                  onChange={e => setActionPersonnelId(e.target.value)}
                  className="form-input"
                  required
                >
                  <option value="">-- Choose Personnel --</option>
                  {(personnelOptions.length > 0 ? personnelOptions : searchResults).map((p: any) => (
                    <option key={p.id} value={p.id}>
                      {p.service_number || p.personnel_code || p.id.slice(0, 8)} - {p.name || p.full_name} ({p.rank || p.rank_or_grade || "Soldier"}) — {p.risk_level || "LOW"} RISK
                    </option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <label className="form-label">Action Type</label>
              <select value={actionType} onChange={e=>setActionType(e.target.value)} className="form-input">
                <option>Monitor</option>
                <option>Contact Personnel</option>
                <option>Welfare Follow-up</option>
                <option>Record Outcome</option>
              </select>
            </div>
            <div>
              <label className="form-label">Notes</label>
              <textarea rows={4} value={actionNotes} onChange={e=>setActionNotes(e.target.value)} required className="form-input resize-none" placeholder="Detailed notes on the welfare action taken..."/>
            </div>
            <div>
              <label className="form-label">Follow-up Date (optional)</label>
              <input type="date" value={actionFollowUpDate} onChange={e=>setActionFollowUpDate(e.target.value)} className="form-input"/>
            </div>
            <div className="flex gap-3 pt-1">
              <button type="button" className="btn-secondary flex-1 justify-center" onClick={() => setIsActionModalOpen(false)}>Cancel</button>
              <button
                type="submit"
                disabled={isSubmittingAction || !actionNotes.trim() || (!selectedPersonnelId && !actionPersonnelId)}
                className="btn-primary flex-1 justify-center disabled:opacity-50"
              >
                {isSubmittingAction ? "Recording..." : "Record Action"}
              </button>
            </div>
          </form>
        </Modal>

      </Shell>
    </RoleGuard>
  );
}
