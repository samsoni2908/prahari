"use client";

import React, { useState, useEffect } from "react";
import {
  HeartHandshake,
  Search,
  Users,
  TrendingUp,
  Activity,
  AlertTriangle,
  Clock,
  Calendar,
  Briefcase,
  ShieldCheck,
  CheckCircle2,
  X,
  Send,
  FileText,
  UserCheck,
  RefreshCw,
  Eye,
  PhoneCall,
  UserCheck2,
  ChevronRight,
  ShieldAlert,
  ArrowRight,
  FileSpreadsheet,
  AlertCircle,
  HelpCircle,
  Award,
  PlusCircle,
  FolderOpen,
  Scale,
  Lock,
} from "lucide-react";
import { welfareApi } from "@/lib/api";
import { RiskBadge, StatusBadge } from "@/components/common/Badges";
import { StatCard } from "@/components/common/Cards";
import { Button } from "@/components/common/Button";
import { SearchInput } from "@/components/common/Input";
import { Drawer } from "@/components/common/Drawer";
import { LoadingState, EmptyState } from "@/components/common/States";

export default function WelfarePage() {
  const [activeTab, setActiveTab] = useState<"search" | "cases">("search");
  const [searchMode, setSearchMode] = useState<"roster" | "audited">("roster");

  // Roster view state
  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<"ALL" | "LOW" | "MEDIUM" | "HIGH">("ALL");
  const [personnelList, setPersonnelList] = useState<any[]>([]);
  const [casesList, setCasesList] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Audited Named Search state
  const [namedField, setNamedField] = useState<"name" | "service_code" | "pseudo_id">("name");
  const [namedQuery, setNamedQuery] = useState("");
  const [namedPurpose, setNamedPurpose] = useState(
    "Authorized welfare case review and personnel support assessment"
  );
  const [namedResults, setNamedResults] = useState<any[] | null>(null);
  const [namedSearching, setNamedSearching] = useState(false);
  const [namedError, setNamedError] = useState<string | null>(null);

  // Open Case Modal State
  const [caseTargetPersonnel, setCaseTargetPersonnel] = useState<any | null>(null);
  const [caseRequestType, setCaseRequestType] = useState<
    "LEAVE_ASSISTANCE" | "STRESS_FATIGUE" | "MEDICAL_HEALTH" | "FAMILY_PERSONAL"
  >("STRESS_FATIGUE");
  const [casePriority, setCasePriority] = useState<"NORMAL" | "URGENT">("NORMAL");
  const [caseReason, setCaseReason] = useState("");
  const [caseSubmitting, setCaseSubmitting] = useState(false);
  const [caseSuccessMsg, setCaseSuccessMsg] = useState<string | null>(null);

  // Case Details Drawer State
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [selectedCaseDetail, setSelectedCaseDetail] = useState<any | null>(null);
  const [caseDetailLoading, setCaseDetailLoading] = useState(false);
  const [caseActionNote, setCaseActionNote] = useState("");
  const [caseActionType, setCaseActionType] = useState<string>("WELFARE_FOLLOWUP");
  const [caseActionFollowUp, setCaseActionFollowUp] = useState("");
  const [caseActionStatus, setCaseActionStatus] = useState("ASSIGNED");
  const [caseActionSubmitting, setCaseActionSubmitting] = useState(false);
  const [caseActionSuccess, setCaseActionSuccess] = useState<string | null>(null);
  const [casePriorityReason, setCasePriorityReason] = useState("");
  const [casePrioritySubmitting, setCasePrioritySubmitting] = useState(false);

  // Selected Profile for 7-tab dossier drawer
  const [selectedPersonnelId, setSelectedPersonnelId] = useState<string | null>(null);
  const [profileData, setProfileData] = useState<any>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileTab, setProfileTab] = useState<
    "overview" | "service" | "deployment" | "leave_rest" | "training" | "wellbeing" | "risk"
  >("overview");

  // Welfare Action recording form inside dossier
  const [actionType, setActionType] = useState<
    "MONITOR" | "CONTACT_PERSONNEL" | "WELFARE_FOLLOWUP" | "RECORD_OUTCOME"
  >("WELFARE_FOLLOWUP");
  const [actionDetails, setActionDetails] = useState("");
  const [actionNotes, setActionNotes] = useState("");
  const [actionFollowUp, setActionFollowUp] = useState("");
  const [actionOutcome, setActionOutcome] = useState("");
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    handleSearch();
    loadCases();

    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get("tab");
      if (tab === "cases") setActiveTab("cases");
      else if (tab === "search" || tab === "personnel") setActiveTab("search");

      const pid = params.get("personnel_id");
      if (pid) {
        openProfile(pid);
      }
    }
  }, [riskFilter]);

  async function handleSearch() {
    setLoading(true);
    setError(null);
    try {
      const data = await welfareApi.searchPersonnel(searchQuery, riskFilter);
      setPersonnelList(data || []);
    } catch (err: any) {
      setError(err.message || "Failed to search personnel");
    } finally {
      setLoading(false);
    }
  }

  async function handleNamedSearch(e: React.FormEvent) {
    e.preventDefault();
    if (namedQuery.trim().length < 3) {
      setNamedError("Search query must be at least 3 characters");
      return;
    }
    if (namedPurpose.trim().length < 5) {
      setNamedError("Purpose reason must be at least 5 characters for compliance audit");
      return;
    }

    setNamedSearching(true);
    setNamedError(null);
    try {
      const resp = await welfareApi.namedSearch({
        field: namedField,
        query: namedQuery.trim(),
        purpose_reason: namedPurpose.trim(),
        limit: 20,
      });
      setNamedResults(resp?.items || []);
    } catch (err: any) {
      setNamedError(err.message || "Audited lookup failed");
    } finally {
      setNamedSearching(false);
    }
  }

  async function loadCases() {
    try {
      const cases = await welfareApi.listCases();
      setCasesList(cases || []);
    } catch {
      // Keep existing silent fallback
    }
  }

  async function openCaseDrawer(caseId: string) {
    setSelectedCaseId(caseId);
    setCaseDetailLoading(true);
    setCaseActionSuccess(null);
    try {
      const detail = await welfareApi.getCaseDetail(caseId);
      setSelectedCaseDetail(detail);
      setCaseActionStatus(detail.status || "ASSIGNED");
    } catch (err: any) {
      setError(err.message || "Failed to load case detail");
    } finally {
      setCaseDetailLoading(false);
    }
  }

  async function openProfile(personnelId: string) {
    setSelectedPersonnelId(personnelId);
    setProfileLoading(true);
    setProfileTab("overview");
    setActionSuccessMsg(null);
    try {
      const profile = await welfareApi.getPersonnelProfile(personnelId);
      setProfileData(profile);
    } catch (err: any) {
      setError(err.message || "Failed to load individual personnel profile");
    } finally {
      setProfileLoading(false);
    }
  }

  async function handleCreateCase(e: React.FormEvent) {
    e.preventDefault();
    if (!caseTargetPersonnel || caseReason.trim().length < 10) {
      setError("Personnel reason must be at least 10 characters");
      return;
    }

    setCaseSubmitting(true);
    setCaseSuccessMsg(null);
    try {
      const res = await welfareApi.openCase({
        personnel_id: caseTargetPersonnel.id,
        request_type: caseRequestType,
        priority: casePriority,
        personnel_visible_reason: caseReason.trim(),
      });
      setCaseSuccessMsg(
        `Support case #${res.id?.slice(0, 8)} opened successfully. Status: ${res.status}`
      );
      setCaseReason("");
      loadCases();
      setTimeout(() => {
        setCaseTargetPersonnel(null);
        setCaseSuccessMsg(null);
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to open support case");
    } finally {
      setCaseSubmitting(false);
    }
  }

  async function handleAssignCaseToMe() {
    if (!selectedCaseId) return;
    try {
      await welfareApi.assignCase(
        selectedCaseId,
        "Welfare Officer self-assigned case for dedicated support"
      );
      setCaseActionSuccess("Case assigned to you successfully.");
      openCaseDrawer(selectedCaseId);
      loadCases();
    } catch (err: any) {
      setError(err.message || "Failed to assign case");
    }
  }

  async function handleUpdateCasePriority(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedCaseId || casePriorityReason.trim().length < 5) return;
    setCasePrioritySubmitting(true);
    try {
      const newPriority = selectedCaseDetail?.priority === "URGENT" ? "NORMAL" : "URGENT";
      await welfareApi.updatePriority(selectedCaseId, newPriority, casePriorityReason.trim());
      setCaseActionSuccess(`Priority updated to ${newPriority}.`);
      setCasePriorityReason("");
      openCaseDrawer(selectedCaseId);
      loadCases();
    } catch (err: any) {
      setError(err.message || "Failed to update priority");
    } finally {
      setCasePrioritySubmitting(false);
    }
  }

  async function handleRecordCaseAction(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedCaseId) return;
    setCaseActionSubmitting(true);
    try {
      await welfareApi.recordCaseAction(selectedCaseId, {
        action_type: caseActionType,
        note: caseActionNote || undefined,
        case_status: caseActionStatus,
        follow_up_date: caseActionFollowUp || undefined,
      });
      setCaseActionSuccess("Case action and status recorded in audit trail.");
      setCaseActionNote("");
      openCaseDrawer(selectedCaseId);
      loadCases();
    } catch (err: any) {
      setError(err.message || "Failed to record case action");
    } finally {
      setCaseActionSubmitting(false);
    }
  }

  async function handleRecordAction(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedPersonnelId || !actionDetails) return;
    setActionSubmitting(true);
    setActionSuccessMsg(null);
    try {
      const res = await welfareApi.recordWelfareAction(selectedPersonnelId, {
        action_type: actionType,
        details: actionDetails,
        notes: actionNotes,
        follow_up_date: actionFollowUp || undefined,
        outcome: actionOutcome || undefined,
      });
      setActionSuccessMsg(
        `Action '${res.action_type || actionType}' recorded successfully in immutable audit trail.`
      );
      setActionDetails("");
      setActionNotes("");
      setActionOutcome("");
      loadCases();
    } catch (err: any) {
      setError(err.message || "Failed to record welfare action");
    } finally {
      setActionSubmitting(false);
    }
  }

  const highRiskCount = personnelList.filter((p) => p.risk_band === "HIGH").length;
  const watchRiskCount = personnelList.filter((p) => p.risk_band === "MEDIUM").length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ─── Header & Telemetry Status ───────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#CFDDCE]">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-serif text-2xl font-bold text-[#182417]">
              Welfare Officer Portal
            </h1>
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#FAF9F5] border border-[#CFDDCE] text-[#5B2C78] font-bold">
              Confidential Support
            </span>
          </div>
          <p className="text-xs text-[#677766] mt-1">
            Authorized Personnel Roster • Purpose-Audited Search • 7-Tab Welfare Dossier • Human-in-the-Loop Interventions
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              handleSearch();
              loadCases();
            }}
            disabled={loading}
            icon={<RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />}
          >
            Refresh Telemetry
          </Button>

          <span className="px-3 py-1.5 rounded-full bg-[#ECFDF5] text-[#15803D] text-xs font-semibold border border-[#A7F3D0] flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4" />
            <span>Row-Level Security Active</span>
          </span>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-[#FEF2F2] text-[#B91C1C] border border-[#FECACA] text-xs flex items-center justify-between gap-2 animate-in fade-in">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="p-1 hover:bg-[#FECACA] rounded">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* ─── Top KPI Stat Cards ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Monitored Personnel"
          value={personnelList.length}
          subtitle="Authorized Unit Scope"
          icon={<Users className="h-4 w-4" />}
          status="normal"
        />
        <StatCard
          title="Attention Required"
          value={highRiskCount}
          subtitle="High Strain / Night Duty Deficit"
          icon={<AlertTriangle className="h-4 w-4" />}
          status={highRiskCount > 0 ? "critical" : "normal"}
        />
        <StatCard
          title="Watch Status"
          value={watchRiskCount}
          subtitle="WSI 40–69 Operational Band"
          icon={<Activity className="h-4 w-4" />}
          status={watchRiskCount > 0 ? "elevated" : "normal"}
        />
        <StatCard
          title="Active Support Cases"
          value={casesList.length}
          subtitle="Scheduled Follow-ups Pending"
          icon={<HeartHandshake className="h-4 w-4" />}
          status="neutral"
        />
      </div>

      {/* ─── Main Tabs Navigation ────────────────────────────────────── */}
      <div className="flex border-b border-[#CFDDCE] space-x-4">
        <button
          onClick={() => setActiveTab("search")}
          className={`pb-3 text-xs md:text-sm font-semibold transition-all relative ${
            activeTab === "search"
              ? "text-[#2C5127]"
              : "text-[#677766] hover:text-[#182417]"
          }`}
        >
          <span>Authorized Personnel Roster ({personnelList.length})</span>
          {activeTab === "search" && (
            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#2C5127] rounded-full" />
          )}
        </button>

        <button
          onClick={() => setActiveTab("cases")}
          className={`pb-3 text-xs md:text-sm font-semibold transition-all relative ${
            activeTab === "cases"
              ? "text-[#2C5127]"
              : "text-[#677766] hover:text-[#182417]"
          }`}
        >
          <span>Active Support Cases ({casesList.length})</span>
          {activeTab === "cases" && (
            <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#2C5127] rounded-full" />
          )}
        </button>
      </div>

      {/* ─── Tab Content: Personnel Roster & Search ──────────────────── */}
      {activeTab === "search" && (
        <div className="space-y-4">
          {/* Mode Selector: Roster vs Audited Lookup */}
          <div className="flex items-center justify-between bg-[#FAF9F5] p-2 rounded-xl border border-[#CFDDCE]">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setSearchMode("roster")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  searchMode === "roster"
                    ? "bg-[#2C5127] text-white shadow-sm"
                    : "text-[#3B4B3A] hover:bg-[#EAF1E9]"
                }`}
              >
                Unit Roster Overview
              </button>
              <button
                onClick={() => setSearchMode("audited")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                  searchMode === "audited"
                    ? "bg-[#5B2C78] text-white shadow-sm"
                    : "text-[#5B2C78] hover:bg-[#F3E8FF]"
                }`}
              >
                <Lock className="h-3 w-3" />
                <span>Audited Personnel Lookup</span>
              </button>
            </div>
            <span className="text-[11px] text-[#677766] font-mono hidden sm:inline">
              {searchMode === "roster"
                ? "Showing authorized unit scope"
                : "All queries recorded in governance ledger"}
            </span>
          </div>

          {searchMode === "audited" ? (
            /* Purpose-Audited Named Search Box */
            <div className="p-5 rounded-2xl bg-white border border-[#D8B4FE] shadow-sm space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-serif text-sm font-bold text-[#182417] flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4 text-[#5B2C78]" />
                    <span>Purpose-Audited Personnel Search (AGENTS.md Contract)</span>
                  </h3>
                  <p className="text-xs text-[#677766] mt-0.5">
                    Direct name and service code lookups require an explicit operational purpose. Each query is signed and written to the immutable audit trail.
                  </p>
                </div>
                <span className="px-2.5 py-1 rounded bg-[#F3E8FF] text-[#5B2C78] font-mono text-[10px] font-bold">
                  AUDITED SCOPE
                </span>
              </div>

              {namedError && (
                <div className="p-3 rounded-lg bg-[#FEF2F2] border border-[#FECACA] text-xs text-[#B91C1C]">
                  {namedError}
                </div>
              )}

              <form onSubmit={handleNamedSearch} className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                      Target Search Field
                    </label>
                    <select
                      value={namedField}
                      onChange={(e) => setNamedField(e.target.value as any)}
                      className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#5B2C78]"
                    >
                      <option value="name">Full Name (Fuzzy)</option>
                      <option value="service_code">Service Code (e.g. P0162)</option>
                      <option value="pseudo_id">Pseudo ID (e.g. PRH-0BD8482D)</option>
                    </select>
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-xs font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                      Search Query (min 3 chars)
                    </label>
                    <input
                      type="text"
                      value={namedQuery}
                      onChange={(e) => setNamedQuery(e.target.value)}
                      placeholder="e.g. Amit Sharma or P0162"
                      required
                      className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#5B2C78]"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                    Purpose &amp; Operational Justification (Required for Audit Logging, min 5 chars)
                  </label>
                  <input
                    type="text"
                    value={namedPurpose}
                    onChange={(e) => setNamedPurpose(e.target.value)}
                    placeholder="e.g. Routine confidential welfare intake review for shift transition"
                    required
                    className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#5B2C78]"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-1">
                  <Button
                    type="submit"
                    loading={namedSearching}
                    icon={<Search className="h-4 w-4" />}
                    className="bg-[#5B2C78] hover:bg-[#4A2462] text-white"
                  >
                    Execute Audited Search
                  </Button>
                </div>
              </form>

              {/* Audited Results List */}
              {namedResults !== null && (
                <div className="pt-3 border-t border-[#E4ECE3]">
                  <h4 className="text-xs font-mono uppercase font-bold text-[#182417] mb-2">
                    Audited Lookup Results ({namedResults.length})
                  </h4>
                  {namedResults.length === 0 ? (
                    <EmptyState
                      title="No Personnel Found"
                      description="No records matched the specified field and query within your authorized scope."
                    />
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {namedResults.map((p) => (
                        <div
                          key={p.id}
                          className="p-4 rounded-xl bg-white border border-[#CFDDCE] hover:border-[#5B2C78] shadow-sm transition-all space-y-2.5"
                        >
                          <div>
                            <div className="font-bold text-sm text-[#182417]">
                              {p.full_name || p.pseudo_id}
                            </div>
                            <div className="text-xs text-[#677766] font-mono">
                              Code: <strong>{p.personnel_code || "N/A"}</strong> • ID: {p.pseudo_id}
                            </div>
                          </div>
                          <div className="flex items-center gap-2 pt-2 border-t border-[#E4ECE3]">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openProfile(p.id)}
                              icon={<Eye className="h-3 w-3" />}
                              className="text-xs"
                            >
                              Dossier
                            </Button>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => setCaseTargetPersonnel(p)}
                              icon={<PlusCircle className="h-3 w-3" />}
                              className="text-xs"
                            >
                              Open Case
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            /* Standard Unit Roster Toolbar */
            <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-4 rounded-xl bg-white border border-[#CFDDCE] shadow-sm">
              <div className="flex-1 max-w-lg">
                <SearchInput
                  value={searchQuery}
                  onChange={(val) => setSearchQuery(val)}
                  onClear={() => {
                    setSearchQuery("");
                    setTimeout(() => handleSearch(), 50);
                  }}
                  placeholder="Search by Pseudo ID, Rank, Role, or Service Code..."
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
              </div>

              {/* Locked 3 Risk Band Filters (AGENTS.md Section 7) */}
              <div className="flex items-center gap-1.5 flex-wrap text-xs">
                <span className="text-[11px] text-[#677766] font-mono uppercase mr-1">
                  Filter Band:
                </span>
                <button
                  onClick={() => setRiskFilter("ALL")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    riskFilter === "ALL"
                      ? "bg-[#2C5127] text-white shadow-sm"
                      : "bg-[#FAF9F5] text-[#3B4B3A] border border-[#CFDDCE] hover:bg-[#EAF1E9]"
                  }`}
                >
                  ALL ({personnelList.length})
                </button>
                <button
                  onClick={() => setRiskFilter("LOW")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    riskFilter === "LOW"
                      ? "bg-[#15803D] text-white shadow-sm"
                      : "bg-[#ECFDF5] text-[#15803D] border border-[#A7F3D0] hover:bg-[#D1FAE5]"
                  }`}
                >
                  LOW (0–39)
                </button>
                <button
                  onClick={() => setRiskFilter("MEDIUM")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    riskFilter === "MEDIUM"
                      ? "bg-[#B45309] text-white shadow-sm"
                      : "bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A] hover:bg-[#FEF3C7]"
                  }`}
                >
                  MEDIUM (40–69)
                </button>
                <button
                  onClick={() => setRiskFilter("HIGH")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    riskFilter === "HIGH"
                      ? "bg-[#B91C1C] text-white shadow-sm"
                      : "bg-[#FEF2F2] text-[#B91C1C] border border-[#FECACA] hover:bg-[#FEE2E2]"
                  }`}
                >
                  HIGH (70–100)
                </button>
              </div>
            </div>
          )}

          {/* Personnel Grid */}
          {searchMode === "roster" && (
            loading ? (
              <LoadingState title="Querying authorized personnel records..." />
            ) : personnelList.length === 0 ? (
              <EmptyState
                title="No Personnel Matching Criteria"
                description="Adjust your search query or reset the risk band filter to view authorized unit personnel."
                action={{
                  label: "Reset Filter",
                  onClick: () => {
                    setSearchQuery("");
                    setRiskFilter("ALL");
                  },
                }}
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {personnelList.map((p) => {
                  const isHigh = p.risk_band === "HIGH";
                  const isMed = p.risk_band === "MEDIUM";

                  return (
                    <div
                      key={p.id}
                      className={`p-5 rounded-2xl bg-white border transition-all shadow-sm hover:shadow-cardHover flex flex-col justify-between ${
                        isHigh
                          ? "border-[#FECACA] border-l-4 border-l-[#B91C1C]"
                          : isMed
                          ? "border-[#FDE68A] border-l-4 border-l-[#B45309]"
                          : "border-[#CFDDCE] border-l-4 border-l-[#15803D]"
                      }`}
                    >
                      <div>
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="font-mono font-bold text-sm text-[#182417] flex items-center gap-2">
                              <span>{p.pseudo_id}</span>
                              <span className="text-[11px] text-[#677766] font-normal">
                                ({p.rank_or_grade})
                              </span>
                            </div>
                            <div className="text-xs font-medium text-[#3B4B3A] mt-0.5">
                              {p.role_title}
                            </div>
                            <div className="text-[11px] text-[#677766] mt-1 flex items-center gap-1 font-mono">
                              <Briefcase className="h-3 w-3" />
                              <span>{p.unit_name}</span>
                            </div>
                          </div>

                          <RiskBadge
                            level={p.risk_band}
                            score={p.risk_score}
                            showScore={true}
                            size="sm"
                          />
                        </div>

                        <div className="mt-3 pt-2 text-[11px] text-[#677766] font-mono flex items-center justify-between">
                          <span>Status: <strong>{p.status || "ACTIVE"}</strong></span>
                          <span>Unit: <strong>{p.unit_name || "Assigned"}</strong></span>
                        </div>
                      </div>

                      <div className="mt-4 pt-3 border-t border-[#E4ECE3] flex items-center justify-between gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setCaseTargetPersonnel(p)}
                          icon={<PlusCircle className="h-3.5 w-3.5" />}
                          className="text-xs flex-1"
                        >
                          Open Case
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => openProfile(p.id)}
                          icon={<ChevronRight className="h-3.5 w-3.5" />}
                          iconPosition="right"
                          className="text-xs flex-1"
                        >
                          Dossier
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )
          )}
        </div>
      )}

      {/* ─── Tab Content: Active Support Cases ───────────────────────── */}
      {activeTab === "cases" && (
        <div className="space-y-4">
          <div className="p-6 rounded-2xl bg-white border border-[#CFDDCE] shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="font-serif text-base font-bold text-[#182417]">
                  Welfare Follow-up &amp; Support Requests
                </h3>
                <p className="text-xs text-[#677766]">
                  Active personnel assistance cases and scheduled follow-up meetings.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={loadCases}
                icon={<RefreshCw className="h-3.5 w-3.5" />}
              >
                Refresh Cases
              </Button>
            </div>

            {casesList.length === 0 ? (
              <EmptyState
                title="No Active Support Cases"
                description="Personnel assistance requests and scheduled follow-ups will appear here."
              />
            ) : (
              <div className="divide-y divide-[#E4ECE3] border border-[#CFDDCE] rounded-xl overflow-hidden">
                {casesList.map((c) => (
                  <div
                    key={c.id}
                    className="p-4 bg-white hover:bg-[#FAF9F5] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs transition-colors"
                  >
                    <div className="space-y-1">
                      <div className="font-mono font-bold text-sm text-[#182417] flex items-center gap-2">
                        <span>{c.pseudo_id}</span>
                        <span className="text-xs text-[#677766]">
                          • Case #{c.id?.slice(0, 8)}
                        </span>
                        {c.assigned_to_me && (
                          <span className="px-2 py-0.5 rounded bg-[#ECFDF5] text-[#15803D] text-[10px] font-bold font-mono">
                            MY CASE
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-[#3B4B3A] flex items-center gap-3 flex-wrap">
                        <span>
                          Type: <strong>{c.request_type}</strong>
                        </span>
                        <span>
                          Priority:{" "}
                          <strong
                            className={
                              c.priority === "URGENT"
                                ? "text-[#B91C1C]"
                                : "text-[#B45309]"
                            }
                          >
                            {c.priority || "NORMAL"}
                          </strong>
                        </span>
                        <span>
                          Status: <StatusBadge status={c.status} size="sm" />
                        </span>
                        <span className="text-[#677766] font-mono">
                          Opened: {new Date(c.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => openCaseDrawer(c.id)}
                        icon={<FolderOpen className="h-3.5 w-3.5" />}
                      >
                        Manage Case
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── Open Support Case Modal Drawer ─────────────────────────── */}
      <Drawer
        isOpen={Boolean(caseTargetPersonnel)}
        onClose={() => setCaseTargetPersonnel(null)}
        title={
          caseTargetPersonnel
            ? `Open Welfare Support Case: ${caseTargetPersonnel.pseudo_id}`
            : "Open Welfare Case"
        }
        subtitle="Record formal assistance intake with personnel-visible justification"
        size="md"
      >
        {caseTargetPersonnel && (
          <div className="space-y-4">
            <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs space-y-1 font-mono">
              <div>
                <strong>Subject:</strong> {caseTargetPersonnel.pseudo_id} ({caseTargetPersonnel.rank_or_grade || "Rank"})
              </div>
              <div>
                <strong>Unit:</strong> {caseTargetPersonnel.unit_name || "Assigned Unit"}
              </div>
              <div>
                <strong>Current Status:</strong> {caseTargetPersonnel.status || "ACTIVE"}
              </div>
            </div>

            {caseSuccessMsg && (
              <div className="p-3 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] text-[#15803D] text-xs flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>{caseSuccessMsg}</span>
              </div>
            )}

            <form onSubmit={handleCreateCase} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-[#3B4B3A] mb-1 font-mono">
                  Support Category / Request Type
                </label>
                <select
                  value={caseRequestType}
                  onChange={(e) => setCaseRequestType(e.target.value as any)}
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                >
                  <option value="STRESS_FATIGUE">Stress &amp; Fatigue Intervention</option>
                  <option value="LEAVE_ASSISTANCE">Leave &amp; Recovery Assistance</option>
                  <option value="MEDICAL_HEALTH">Medical / Physical Health Escalation</option>
                  <option value="FAMILY_PERSONAL">Family &amp; Personal Welfare Support</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-[#3B4B3A] mb-1 font-mono">
                  Priority Level
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setCasePriority("NORMAL")}
                    className={`flex-1 py-2 text-xs font-semibold rounded-lg border transition-all ${
                      casePriority === "NORMAL"
                        ? "bg-[#2C5127] text-white border-[#2C5127]"
                        : "bg-white text-[#3B4B3A] border-[#CFDDCE]"
                    }`}
                  >
                    NORMAL
                  </button>
                  <button
                    type="button"
                    onClick={() => setCasePriority("URGENT")}
                    className={`flex-1 py-2 text-xs font-semibold rounded-lg border transition-all ${
                      casePriority === "URGENT"
                        ? "bg-[#B91C1C] text-white border-[#B91C1C]"
                        : "bg-white text-[#3B4B3A] border-[#CFDDCE]"
                    }`}
                  >
                    URGENT
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-[#3B4B3A] mb-1 font-mono">
                  Personnel-Visible Justification (min 10 characters)
                </label>
                <textarea
                  rows={4}
                  value={caseReason}
                  onChange={(e) => setCaseReason(e.target.value)}
                  placeholder="Explain why this welfare case is being initiated. This justification will be visible to the individual personnel in their support log."
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
                <p className="text-[11px] text-[#677766] mt-1">
                  Ethical notice: Per PRAHARI Rules, personnel have right to inspect why a welfare case was opened.
                </p>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setCaseTargetPersonnel(null)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  loading={caseSubmitting}
                  disabled={caseSubmitting || caseReason.trim().length < 10}
                  icon={<PlusCircle className="h-4 w-4" />}
                >
                  Open Official Support Case
                </Button>
              </div>
            </form>
          </div>
        )}
      </Drawer>

      {/* ─── Case Details & Management Drawer ────────────────────────── */}
      <Drawer
        isOpen={Boolean(selectedCaseId)}
        onClose={() => setSelectedCaseId(null)}
        title={
          selectedCaseDetail
            ? `Case #${selectedCaseDetail.id?.slice(0, 8)} — ${selectedCaseDetail.pseudo_id}`
            : "Case Details"
        }
        subtitle={
          selectedCaseDetail
            ? `${selectedCaseDetail.rank_or_grade || "Personnel"} • ${selectedCaseDetail.unit?.unit_name || "Unit"}`
            : "Welfare Case Record"
        }
        badge={
          selectedCaseDetail ? (
            <StatusBadge status={selectedCaseDetail.status} size="sm" />
          ) : null
        }
        size="lg"
      >
        {caseDetailLoading ? (
          <LoadingState title="Loading case telemetry & history..." />
        ) : selectedCaseDetail ? (
          <div className="space-y-6 text-xs">
            {caseActionSuccess && (
              <div className="p-3 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] text-[#15803D] flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>{caseActionSuccess}</span>
              </div>
            )}

            {/* Case Basic Information */}
            <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-2">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div>
                  <div className="text-[10px] text-[#677766] uppercase font-mono">Category</div>
                  <div className="font-bold text-[#182417] mt-0.5 font-mono">
                    {selectedCaseDetail.request_type}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-[#677766] uppercase font-mono">Priority</div>
                  <div className={`font-bold mt-0.5 font-mono ${selectedCaseDetail.priority === "URGENT" ? "text-[#B91C1C]" : "text-[#15803D]"}`}>
                    {selectedCaseDetail.priority || "NORMAL"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-[#677766] uppercase font-mono">Opened Date</div>
                  <div className="font-bold text-[#182417] mt-0.5 font-mono">
                    {new Date(selectedCaseDetail.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-[#677766] uppercase font-mono">Follow-up</div>
                  <div className="font-bold text-[#182417] mt-0.5 font-mono">
                    {selectedCaseDetail.follow_up_date || "None scheduled"}
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-[#CFDDCE]">
                <div className="text-[10px] text-[#677766] uppercase font-mono">Reason on File</div>
                <div className="text-xs text-[#3B4B3A] mt-0.5 font-mono">
                  {selectedCaseDetail.request_text || "No notes recorded"}
                </div>
              </div>
            </div>

            {/* Quick Actions Bar */}
            <div className="flex flex-wrap gap-2 items-center">
              <Button
                variant="outline"
                size="sm"
                onClick={handleAssignCaseToMe}
                icon={<UserCheck className="h-3.5 w-3.5" />}
              >
                Assign Case to Me
              </Button>

              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  if (selectedCaseDetail.personnel_id) {
                    openProfile(selectedCaseDetail.personnel_id);
                  }
                }}
                icon={<Eye className="h-3.5 w-3.5" />}
              >
                View 7-Tab Dossier
              </Button>
            </div>

            {/* Priority Toggle Form */}
            <div className="p-4 rounded-xl bg-white border border-[#CFDDCE] space-y-3">
              <h4 className="font-bold text-[#182417] uppercase tracking-wider font-mono text-[11px] flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5 text-[#B45309]" />
                <span>Update Case Priority</span>
              </h4>
              <form onSubmit={handleUpdateCasePriority} className="space-y-2">
                <input
                  type="text"
                  value={casePriorityReason}
                  onChange={(e) => setCasePriorityReason(e.target.value)}
                  placeholder="Justification for priority escalation/de-escalation (min 5 chars)..."
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
                <Button
                  type="submit"
                  size="sm"
                  variant="outline"
                  loading={casePrioritySubmitting}
                  disabled={casePriorityReason.trim().length < 5 || casePrioritySubmitting}
                >
                  Toggle Priority ({selectedCaseDetail.priority === "URGENT" ? "To NORMAL" : "To URGENT"})
                </Button>
              </form>
            </div>

            {/* Record Action / Update Status Form */}
            <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-3">
              <h4 className="font-bold text-[#182417] uppercase tracking-wider font-mono text-[11px] flex items-center gap-1.5">
                <HeartHandshake className="h-3.5 w-3.5 text-[#5B2C78]" />
                <span>Log Action &amp; Transition Status</span>
              </h4>

              <form onSubmit={handleRecordCaseAction} className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                      Action Type
                    </label>
                    <select
                      value={caseActionType}
                      onChange={(e) => setCaseActionType(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                    >
                      <option value="MONITOR">1. Routine Welfare Monitoring</option>
                      <option value="CONTACT_PERSONNEL">2. Contact &amp; 1-on-1 Interview</option>
                      <option value="WELFARE_FOLLOWUP">3. Operational Welfare Follow-up</option>
                      <option value="RECORD_OUTCOME">4. Final Resolution &amp; Outcome</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                      New Case Status
                    </label>
                    <select
                      value={caseActionStatus}
                      onChange={(e) => setCaseActionStatus(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                    >
                      <option value="OPEN">OPEN</option>
                      <option value="ASSIGNED">ASSIGNED</option>
                      <option value="IN_PROGRESS">IN_PROGRESS</option>
                      <option value="RESOLVED">RESOLVED</option>
                      <option value="CLOSED">CLOSED</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                    Scheduled Follow-up Date (Optional)
                  </label>
                  <input
                    type="date"
                    value={caseActionFollowUp}
                    onChange={(e) => setCaseActionFollowUp(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                    Intervention Notes / Clinical Welfare Record
                  </label>
                  <textarea
                    rows={3}
                    value={caseActionNote}
                    onChange={(e) => setCaseActionNote(e.target.value)}
                    placeholder="Document interview findings, rest interventions, or outcome notes..."
                    className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                  />
                </div>

                <Button
                  type="submit"
                  size="sm"
                  loading={caseActionSubmitting}
                  disabled={caseActionSubmitting}
                  icon={<Send className="h-3.5 w-3.5" />}
                >
                  Commit Action &amp; Status to Audit Ledger
                </Button>
              </form>
            </div>
          </div>
        ) : null}
      </Drawer>

      {/* ─── 7-Tab Personnel Welfare Dossier Drawer ──────────────────── */}
      <Drawer
        isOpen={Boolean(selectedPersonnelId)}
        onClose={() => setSelectedPersonnelId(null)}
        title={
          profileData?.overview?.pseudo_id
            ? `${profileData.overview.pseudo_id} (${profileData.overview.rank_or_grade || "Rank"})`
            : "Personnel Welfare Dossier"
        }
        subtitle={
          profileData?.overview?.unit?.unit_name
            ? `Unit: ${profileData.overview.unit.unit_name} • Service Years: ${profileData.overview.service_years || "N/A"}`
            : "Authorized Welfare File"
        }
        badge={
          profileData?.overview?.risk_band ? (
            <RiskBadge
              level={profileData.overview.risk_band}
              score={profileData.overview.risk_score}
              showScore={true}
              size="sm"
            />
          ) : null
        }
        size="xl"
      >
        {profileLoading ? (
          <LoadingState title="Decrypting and loading 7-tab personnel dossier..." />
        ) : profileData ? (
          <div className="space-y-6">
            {/* 7 Tabs Header per AGENTS.md Section 11 */}
            <div className="flex border-b border-[#CFDDCE] pb-1 gap-2 overflow-x-auto">
              {[
                { id: "overview", label: "Overview", icon: Users },
                { id: "service", label: "Service History", icon: Clock },
                { id: "deployment", label: "Deployment", icon: Briefcase },
                { id: "leave_rest", label: "Leave & Rest", icon: Calendar },
                { id: "training", label: "Training", icon: Award },
                { id: "wellbeing", label: "Well-being", icon: Activity },
                { id: "risk", label: "Risk Analysis", icon: TrendingUp },
              ].map((tab) => {
                const Icon = tab.icon;
                const isSelected = profileTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setProfileTab(tab.id as any)}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                      isSelected
                        ? "bg-[#2C5127] text-white shadow-sm"
                        : "bg-[#FAF9F5] text-[#3B4B3A] hover:bg-[#EAF1E9]"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Tab 1: Overview */}
            {profileTab === "overview" && (
              <div className="space-y-5">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                    <div className="text-[10px] text-[#677766] uppercase font-mono">Status</div>
                    <div className="font-bold text-sm text-[#182417] mt-1 font-mono">
                      {profileData.overview.status}
                    </div>
                  </div>
                  <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                    <div className="text-[10px] text-[#677766] uppercase font-mono">Joining Date</div>
                    <div className="font-bold text-sm text-[#182417] mt-1 font-mono">
                      {profileData.overview.joining_date || "N/A"}
                    </div>
                  </div>
                  <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                    <div className="text-[10px] text-[#677766] uppercase font-mono">Active Alerts</div>
                    <div className="font-bold text-sm text-[#B91C1C] mt-1 font-mono">
                      {profileData.overview.active_alerts_count}
                    </div>
                  </div>
                  <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                    <div className="text-[10px] text-[#677766] uppercase font-mono">Location Sector</div>
                    <div className="font-bold text-sm text-[#182417] mt-1 font-mono">
                      {profileData.overview.unit?.location_label || "Northern"}
                    </div>
                  </div>
                </div>

                {profileData.overview.alerts && profileData.overview.alerts.length > 0 && (
                  <div className="p-4 rounded-xl bg-[#FEF2F2] border border-[#FECACA] space-y-2">
                    <h4 className="text-xs font-bold text-[#B91C1C] uppercase flex items-center gap-1.5">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Active Welfare Trigger Signals</span>
                    </h4>
                    {profileData.overview.alerts.map((a: any) => (
                      <div
                        key={a.id}
                        className="text-xs text-[#7F1D1D] flex items-start gap-2 pt-1 border-t border-[#FCA5A5]/40"
                      >
                        <div>
                          <strong className="font-mono">{a.alert_type}:</strong> {a.message}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Service History */}
            {profileTab === "service" && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-[#3B4B3A] uppercase font-mono">
                  Historical Postings &amp; Unit Transfers
                </h4>
                {profileData.service_history && profileData.service_history.length > 0 ? (
                  profileData.service_history.map((post: any) => (
                    <div
                      key={post.id}
                      className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs space-y-1"
                    >
                      <div className="font-semibold text-[#182417]">
                        {post.posting_type} • {post.location_label}
                      </div>
                      <div className="text-[#677766] text-[11px] font-mono">
                        {post.start_date} to {post.end_date || "Present"}
                      </div>
                      {post.notes && (
                        <div className="text-[#3B4B3A] text-[11px] pt-1">{post.notes}</div>
                      )}
                    </div>
                  ))
                ) : (
                  <EmptyState title="No prior postings on record" description="Initial unit posting." />
                )}
              </div>
            )}

            {/* Tab 3: Deployment */}
            {profileTab === "deployment" && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-[#3B4B3A] uppercase font-mono">
                  Operational Deployments
                </h4>
                {profileData.deployment && profileData.deployment.length > 0 ? (
                  profileData.deployment.map((d: any) => (
                    <div
                      key={d.id}
                      className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs space-y-1"
                    >
                      <div className="font-semibold text-[#182417]">
                        {d.deployment_type} ({d.location_label})
                      </div>
                      <div className="text-[#677766] text-[11px] font-mono">
                        {d.start_date} to {d.end_date || "Active"} • Intensity: Level{" "}
                        {d.intensity_level || 3}/5
                      </div>
                    </div>
                  ))
                ) : (
                  <EmptyState
                    title="No Field Deployments Recorded"
                    description="Standard base duty rotation."
                  />
                )}
              </div>
            )}

            {/* Tab 4: Leave & Rest */}
            {profileTab === "leave_rest" && (
              <div className="space-y-5">
                <div>
                  <h4 className="text-xs font-bold text-[#3B4B3A] uppercase font-mono mb-2">
                    Leave Records (Last 180 Days)
                  </h4>
                  <div className="space-y-2">
                    {profileData.leave_and_rest?.leaves &&
                    profileData.leave_and_rest.leaves.length > 0 ? (
                      profileData.leave_and_rest.leaves.map((l: any) => (
                        <div
                          key={l.id}
                          className="p-3 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs flex justify-between items-center"
                        >
                          <div>
                            <span className="font-semibold text-[#182417]">{l.leave_type}</span>
                            <span className="text-[#677766] font-mono ml-2">({l.days} days)</span>
                          </div>
                          <span className="font-mono text-[#15803D] font-bold">{l.status}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-[#677766] p-3 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                        No recent leaves taken.
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-bold text-[#3B4B3A] uppercase font-mono mb-2">
                    Recent Rest &amp; Disturbance Records
                  </h4>
                  <div className="space-y-2">
                    {profileData.leave_and_rest?.rests &&
                    profileData.leave_and_rest.rests.length > 0 ? (
                      profileData.leave_and_rest.rests.map((r: any) => (
                        <div
                          key={r.id}
                          className="p-3 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs flex justify-between font-mono items-center"
                        >
                          <span>
                            Date: {r.record_date} • Rest Hours: {r.rest_hours} hrs
                          </span>
                          <span
                            className={
                              r.is_disturbed
                                ? "text-[#B91C1C] font-bold"
                                : "text-[#15803D] font-semibold"
                            }
                          >
                            {r.is_disturbed ? "Disturbed Rest" : "Uninterrupted"}
                          </span>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-[#677766] p-3 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                        Rest telemetry aggregated from shift logs.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Tab 5: Training */}
            {profileTab === "training" && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-[#3B4B3A] uppercase font-mono">
                  Training &amp; Drills History
                </h4>
                {profileData.training && profileData.training.length > 0 ? (
                  profileData.training.map((t: any) => (
                    <div
                      key={t.id}
                      className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs flex justify-between items-center"
                    >
                      <div>
                        <div className="font-semibold text-[#182417]">{t.training_name}</div>
                        <div className="text-[11px] text-[#677766] font-mono">
                          {t.start_date} to {t.end_date} • {t.hours || 0} hrs
                        </div>
                      </div>
                      <span className="px-2.5 py-1 rounded bg-[#ECFDF5] text-[#15803D] font-mono text-[11px] font-semibold">
                        {t.status}
                      </span>
                    </div>
                  ))
                ) : (
                  <EmptyState title="No Specialized Courses" description="Mandatory annual fitness only." />
                )}
              </div>
            )}

            {/* Tab 6: Well-being */}
            {profileTab === "wellbeing" && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-[#182417]">
                      Confidential Self-Check Metadata
                    </span>
                    <span className="font-mono text-[#15803D] font-semibold">
                      Consent: {profileData.wellbeing?.consent_status || "ACTIVE"}
                    </span>
                  </div>
                  <p className="text-xs text-[#3B4B3A] leading-relaxed">
                    Personnel has completed{" "}
                    <strong>{profileData.wellbeing?.assessments_count || 0}</strong> voluntary
                    confidential assessments. Per AGENTS.md Section 4, raw private answer texts remain
                    strictly protected and isolated from operational analytics.
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-[#3B4B3A] uppercase font-mono">
                    Assessment History (Metadata Only)
                  </h4>
                  {profileData.wellbeing?.recent_assessments &&
                  profileData.wellbeing.recent_assessments.length > 0 ? (
                    profileData.wellbeing.recent_assessments.map((chk: any) => (
                      <div
                        key={chk.id}
                        className="p-3 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs flex justify-between items-center font-mono"
                      >
                        <span>
                          Date: {chk.assessment_date} • {chk.instrument_name}
                        </span>
                        <span className="text-[#15803D] font-semibold">
                          STATUS: {chk.status}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="text-xs text-[#677766] p-3 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                      No historical self-checks on file.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tab 7: Risk Analysis */}
            {profileTab === "risk" && (
              <div className="space-y-5">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                    <div className="text-[10px] text-[#677766] uppercase font-mono">
                      Current WSI Index
                    </div>
                    <div className="font-bold text-lg text-[#2C5127] mt-1 font-mono">
                      {profileData.risk_analysis?.current_wsi !== null &&
                      profileData.risk_analysis?.current_wsi !== undefined
                        ? profileData.risk_analysis.current_wsi
                        : "NOT_COMPUTED"}{" "}
                      ({profileData.risk_analysis?.risk_band || "NOT_COMPUTED"})
                    </div>
                  </div>

                  <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                    <div className="text-[10px] text-[#677766] uppercase font-mono">
                      Workload EWMA vs Baseline
                    </div>
                    <div className="font-bold text-lg text-[#182417] mt-1 font-mono">
                      {profileData.risk_analysis?.baseline?.current_value !== undefined &&
                      profileData.risk_analysis?.baseline?.baseline_mean !== undefined
                        ? `${profileData.risk_analysis.baseline.current_value} / ${profileData.risk_analysis.baseline.baseline_mean}`
                        : "NOT_COMPUTED"}
                    </div>
                  </div>

                  <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                    <div className="text-[10px] text-[#677766] uppercase font-mono">
                      Leave Anomaly Risk (30d)
                    </div>
                    <div className="font-bold text-lg text-[#B45309] mt-1 font-mono">
                      {profileData.risk_analysis?.prediction?.target_leave_anomaly_prob !== null &&
                      profileData.risk_analysis?.prediction?.target_leave_anomaly_prob !== undefined
                        ? `${Math.round(
                            profileData.risk_analysis.prediction.target_leave_anomaly_prob * 100
                          )}%`
                        : profileData.risk_analysis?.prediction?.status || "MODEL_UNAVAILABLE"}
                    </div>
                  </div>
                </div>

                {/* Evidence Convergence Card (Truthful Governance) */}
                {profileData.risk_analysis?.evidence_convergence && (
                  <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-[#182417] flex items-center gap-1.5">
                        <Scale className="h-4 w-4 text-[#2C5127]" />
                        <span>Evidence Convergence Protocol</span>
                      </span>
                      <span className="font-mono text-xs font-bold text-[#5B2C78]">
                        {profileData.risk_analysis.evidence_convergence.convergence_state || "OPERATIONAL_EVIDENCE_ONLY"}
                      </span>
                    </div>
                    <p className="text-xs text-[#3B4B3A]">
                      {profileData.risk_analysis.evidence_convergence.explanation}
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 text-[11px] font-mono border-t border-[#E4ECE3]">
                      <div className="p-2 rounded bg-white border border-[#CFDDCE]">
                        <span className="text-[#677766]">Operational Evidence: </span>
                        <strong>{profileData.risk_analysis.evidence_convergence.operational_evidence?.status || "AVAILABLE"}</strong>
                      </div>
                      <div className="p-2 rounded bg-white border border-[#CFDDCE]">
                        <span className="text-[#677766]">Private Wellbeing Evidence: </span>
                        <strong>{profileData.risk_analysis.evidence_convergence.private_wellbeing_evidence?.status || "NOT_SHARED"}</strong>
                      </div>
                    </div>
                  </div>
                )}

                <div>
                  <h4 className="text-xs font-bold text-[#3B4B3A] uppercase font-mono mb-2">
                    Contributing Operational Drivers
                  </h4>
                  <div className="space-y-2">
                    {profileData.risk_analysis?.contributing_factors &&
                    profileData.risk_analysis.contributing_factors.length > 0 ? (
                      profileData.risk_analysis.contributing_factors.map(
                        (f: any, idx: number) => (
                          <div
                            key={idx}
                            className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs space-y-1"
                          >
                            <div className="font-semibold text-[#182417] flex items-center justify-between">
                              <span>{f.factor}</span>
                              <span
                                className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                                  f.severity === "HIGH"
                                    ? "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]"
                                    : "bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]"
                                }`}
                              >
                                {f.severity}
                              </span>
                            </div>
                            <div className="text-[11px] text-[#3B4B3A]">{f.detail}</div>
                          </div>
                        )
                      )
                    ) : (
                      <div className="text-xs text-[#677766] p-3 bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                        All operational factors within normal baseline parameters.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ─── Welfare Action Recording Form (Human-in-the-Loop) ─── */}
            <div className="mt-8 pt-6 border-t border-[#CFDDCE] bg-[#FAF9F5] p-5 rounded-2xl border border-[#CFDDCE] space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <HeartHandshake className="h-4 w-4 text-[#5B2C78]" />
                  <h4 className="text-xs font-bold text-[#182417] uppercase tracking-wider font-mono">
                    Log Human Welfare Intervention
                  </h4>
                </div>
                <span className="text-[10px] text-[#677766] font-mono">
                  Immutable Audit Ledger
                </span>
              </div>

              {actionSuccessMsg && (
                <div className="p-3 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] text-[#15803D] text-xs flex items-center gap-2 animate-in fade-in">
                  <CheckCircle2 className="h-4 w-4 shrink-0" />
                  <span>{actionSuccessMsg}</span>
                </div>
              )}

              <form onSubmit={handleRecordAction} className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: "MONITOR", label: "1. Monitor" },
                    { id: "CONTACT_PERSONNEL", label: "2. Contact" },
                    { id: "WELFARE_FOLLOWUP", label: "3. Follow-up" },
                    { id: "RECORD_OUTCOME", label: "4. Record Outcome" },
                  ].map((act) => (
                    <button
                      key={act.id}
                      type="button"
                      onClick={() => setActionType(act.id as any)}
                      className={`p-2.5 rounded-lg text-xs font-semibold border transition-all text-center ${
                        actionType === act.id
                          ? "bg-[#2C5127] text-white border-[#244320] shadow-sm"
                          : "bg-white border-[#CFDDCE] text-[#3B4B3A] hover:bg-[#EAF1E9]"
                      }`}
                    >
                      {act.label}
                    </button>
                  ))}
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#3B4B3A] mb-1.5 font-mono">
                    Action Details &amp; Operational Intervention Description
                  </label>
                  <input
                    type="text"
                    value={actionDetails}
                    onChange={(e) => setActionDetails(e.target.value)}
                    placeholder="e.g. Conducted 1-on-1 fatigue interview and scheduled 48h recovery rest window..."
                    required
                    className="w-full px-3.5 py-2.5 bg-white border border-[#CFDDCE] rounded-lg text-xs md:text-sm text-[#182417] placeholder-[#9AA899] focus:outline-none focus:ring-2 focus:ring-[#2C5127] font-mono"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[#3B4B3A] mb-1.5 font-mono">
                      Scheduled Follow-up Date
                    </label>
                    <input
                      type="date"
                      value={actionFollowUp}
                      onChange={(e) => setActionFollowUp(e.target.value)}
                      className="w-full px-3.5 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127] font-mono"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-wider text-[#3B4B3A] mb-1.5 font-mono">
                      Verified Outcome (If Resolving Case)
                    </label>
                    <input
                      type="text"
                      value={actionOutcome}
                      onChange={(e) => setActionOutcome(e.target.value)}
                      placeholder="e.g. 14-day strain index reduced to normal baseline"
                      className="w-full px-3.5 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs text-[#182417] placeholder-[#9AA899] focus:outline-none focus:ring-2 focus:ring-[#2C5127] font-mono"
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={actionSubmitting || !actionDetails}
                  loading={actionSubmitting}
                  icon={<Send className="h-4 w-4" />}
                >
                  Log Welfare Action to Audit
                </Button>
              </form>
            </div>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
