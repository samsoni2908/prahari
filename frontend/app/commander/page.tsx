"use client";

import React, { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Users,
  Activity,
  AlertTriangle,
  TrendingUp,
  ShieldCheck,
  RefreshCw,
  Clock,
  Calendar,
  Compass,
  FileText,
  BarChart3,
  Layers,
  CheckCircle2,
  Briefcase,
  AlertCircle,
  Sliders,
  Sparkles,
  Check,
  X,
  Eye,
  SlidersHorizontal,
  ChevronRight,
  ShieldAlert,
} from "lucide-react";
import { commanderApi, type CommanderOverview } from "@/lib/api";
import WsiTrendChart from "@/components/charts/WsiTrendChart";
import WsiDonutChart from "@/components/charts/WsiDonutChart";
import DriverBarChart from "@/components/charts/DriverBarChart";
import { StatCard } from "@/components/common/Cards";
import { Button } from "@/components/common/Button";
import { ChartContainer } from "@/components/common/ChartContainer";
import { Drawer } from "@/components/common/Drawer";
import { RiskBadge, StatusBadge } from "@/components/common/Badges";
import { LoadingState, EmptyState } from "@/components/common/States";

export default function CommanderPage() {
  const [activeTab, setActiveTab] = useState<
    "overview" | "priority" | "alerts" | "scenarios" | "workload" | "deployments" | "leave" | "trends"
  >("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  // Aggregate Data states
  const [overview, setOverview] = useState<CommanderOverview | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [deployments, setDeployments] = useState<any>(null);
  const [leaveData, setLeaveData] = useState<any>(null);
  const [workloadData, setWorkloadData] = useState<any>(null);
  const [riskTrends, setRiskTrends] = useState<any[]>([]);

  // Operational decision states
  const [priorityList, setPriorityList] = useState<any[]>([]);
  const [alertsList, setAlertsList] = useState<any[]>([]);
  const [scenariosList, setScenariosList] = useState<any[]>([]);

  // Strain card drawer state
  const [selectedStrainPerson, setSelectedStrainPerson] = useState<any | null>(null);
  const [strainCardLoading, setStrainCardLoading] = useState(false);
  const [strainCardData, setStrainCardData] = useState<any | null>(null);

  // Action states
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  useEffect(() => {
    loadData();

    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get("tab");
      if (tab === "priority" || tab === "attention") setActiveTab("priority");
      else if (tab === "alerts") setActiveTab("alerts");
      else if (tab === "scenarios" || tab === "balance") setActiveTab("scenarios");
      else if (tab === "workload") setActiveTab("workload");
      else if (tab === "deployments" || tab === "deployment") setActiveTab("deployments");
      else if (tab === "leave") setActiveTab("leave");
      else if (tab === "trends" || tab === "risk-trends") setActiveTab("trends");
      else if (tab === "overview" || tab === "unit") setActiveTab("overview");
    }
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [ov, st, dep, lv, wl, tr, pri, al, sc] = await Promise.all([
        commanderApi.getOverview().catch(() => null),
        commanderApi.getUnitStats().catch(() => null),
        commanderApi.getDeployments().catch(() => null),
        commanderApi.getLeave().catch(() => null),
        commanderApi.getWorkload().catch(() => null),
        commanderApi.getRiskTrends().catch(() => []),
        commanderApi.getPriorityList().catch(() => []),
        commanderApi.getAlerts().catch(() => ({ items: [] })),
        commanderApi.getScenarios().catch(() => []),
      ]);

      setOverview(ov);
      setStats(st);
      setDeployments(dep);
      setLeaveData(lv);
      setWorkloadData(wl);
      setRiskTrends(tr || []);
      setPriorityList(pri || []);
      setAlertsList(al?.items || []);
      setScenariosList(sc || []);
    } catch (err: any) {
      setError(err.message || "Failed to load commander unit data");
    } finally {
      setLoading(false);
    }
  }

  async function handleOpenStrainCard(person: any) {
    setSelectedStrainPerson(person);
    setStrainCardLoading(true);
    try {
      const card = await commanderApi.getStrainCard(person.personnel_id);
      setStrainCardData(card);
    } catch {
      setStrainCardData(null);
    } finally {
      setStrainCardLoading(false);
    }
  }

  async function handleAcknowledgeAlert(alertId: string) {
    setActionInProgress(alertId);
    setFeedbackMsg(null);
    try {
      await commanderApi.acknowledgeAlert(alertId, "Acknowledged during commander daily operational review");
      setFeedbackMsg("Alert acknowledged successfully.");
      const updated = await commanderApi.getAlerts();
      setAlertsList(updated.items || []);
    } catch (err: any) {
      setError(err.message || "Failed to acknowledge alert");
    } finally {
      setActionInProgress(null);
    }
  }

  async function handleResolveAlert(alertId: string) {
    setActionInProgress(alertId);
    setFeedbackMsg(null);
    try {
      await commanderApi.resolveAlert(alertId, "Resolved following roster adjustment and rest verification");
      setFeedbackMsg("Alert resolved and verified.");
      const updated = await commanderApi.getAlerts();
      setAlertsList(updated.items || []);
    } catch (err: any) {
      setError(err.message || "Failed to resolve alert");
    } finally {
      setActionInProgress(null);
    }
  }

  async function handleDecideScenario(scenarioId: string, decision: "ACCEPT" | "MODIFY" | "REJECT", expectedRevision: string) {
    setActionInProgress(scenarioId);
    setFeedbackMsg(null);
    try {
      const rationale =
        decision === "ACCEPT"
          ? "Approved by commander: Roster balancing mitigates night-shift strain while maintaining coverage"
          : decision === "MODIFY"
          ? "Modified by commander: Adjusting schedule parameters for upcoming operational exercise"
          : "Rejected by commander: Unit deployment constraints preclude shift reassignments at this time";

      await commanderApi.decideScenario(scenarioId, {
        decision,
        expected_revision: expectedRevision,
        rationale,
      });

      setFeedbackMsg(`Scenario decision recorded: ${decision}. Action audited.`);
      const updated = await commanderApi.getScenarios();
      setScenariosList(updated || []);
    } catch (err: any) {
      setError(err.message || `Failed to record ${decision} decision`);
    } finally {
      setActionInProgress(null);
    }
  }

  // Risk distribution buckets (strictly 3 locked bands per AGENTS.md Section 6)
  const totalCount: number | null = overview?.kpis.total_personnel ?? null;
  const donutBuckets = overview?.distribution ?? [];

  // Drivers for bar chart
  const drivers = overview?.drivers ?? [];

  // Trend data strictly from real backend responses; never fabricate points
  const trendPoints = riskTrends.map((t: any) => ({
    date: t.date || t.snapshot_date,
    wsi: Math.round(t.mean_wsi || t.wsi || 0),
  }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ─── Header & Telemetry Status ───────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#CFDDCE]">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-serif text-2xl font-bold text-[#182417]">
              Commander Operational Suite
            </h1>
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#EAF1E9] border border-[#CFDDCE] text-[#2C5127] font-bold">
              Unit-Level Aggregates
            </span>
          </div>
          <p className="text-xs text-[#677766] mt-1">
            Unit:{" "}
            <strong className="text-[#182417]">
              {overview?.unit?.unit_name || stats?.unit_name || "Assigned Command Unit"}
            </strong>{" "}
            ({overview?.unit?.unit_code || "Unit"}) • Coverage:{" "}
            <strong className="text-[#15803D]">
              {overview?.kpis?.coverage_percent !== null && overview?.kpis?.coverage_percent !== undefined
                ? `${overview.kpis.coverage_percent}%`
                : "NOT_COMPUTED"}
            </strong>
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
            Refresh Telemetry
          </Button>

          <span className="px-3 py-1.5 rounded-full bg-[#ECFDF5] text-[#15803D] text-xs font-semibold border border-[#A7F3D0] flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4" />
            <span>Operational Equilibrium</span>
          </span>
        </div>
      </div>

      {feedbackMsg && (
        <div className="p-3.5 rounded-xl bg-[#ECFDF5] text-[#15803D] border border-[#A7F3D0] text-xs flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{feedbackMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-3.5 rounded-xl bg-[#FEF2F2] text-[#B91C1C] border border-[#FECACA] text-xs flex items-center gap-2 animate-in fade-in">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ─── Tabs Navigation ─────────────────────────────────────────── */}
      <div className="flex border-b border-[#CFDDCE] space-x-2 overflow-x-auto">
        {[
          { id: "overview", label: "Unit Overview", icon: LayoutDashboard },
          { id: "priority", label: "Priority Attention Roster", icon: Users },
          { id: "alerts", label: "Operational Alerts", icon: AlertTriangle },
          { id: "scenarios", label: "BALANCE Scenarios", icon: SlidersHorizontal },
          { id: "workload", label: "Workload Strain", icon: Activity },
          { id: "deployments", label: "Deployments", icon: Briefcase },
          { id: "leave", label: "Leave & Rest", icon: Calendar },
          { id: "trends", label: "Risk Trends", icon: TrendingUp },
        ].map((tab) => {
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-3 text-xs md:text-sm font-semibold transition-all relative whitespace-nowrap px-3 flex items-center gap-1.5 ${
                isSelected ? "text-[#2C5127]" : "text-[#677766] hover:text-[#182417]"
              }`}
            >
              <span>{tab.label}</span>
              {tab.id === "alerts" && alertsList.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-[#B91C1C] text-white text-[10px] font-bold">
                  {alertsList.length}
                </span>
              )}
              {isSelected && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#2C5127] rounded-full" />
              )}
            </button>
          );
        })}
      </div>

      {/* ─── Tab Content: Overview ───────────────────────────────────── */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard
              title="Sanctioned Strength"
              value={overview?.unit.sanctioned_strength ?? "—"}
              subtitle="Unit Master Establishment"
              icon={<Users className="h-4 w-4" />}
              status="normal"
            />
            <StatCard
              title="Available Strength"
              value={overview?.kpis?.available_strength ?? stats?.available_strength ?? "NOT_COMPUTED"}
              subtitle="Active Operational Ready"
              icon={<CheckCircle2 className="h-4 w-4" />}
              status="normal"
            />
            <StatCard
              title="Mean Unit WSI"
              value={overview?.kpis.avg_wsi !== null && overview?.kpis.avg_wsi !== undefined ? overview.kpis.avg_wsi : "NOT_COMPUTED"}
              subtitle="Governed 7-factor index (0-100)"
              icon={<Activity className="h-4 w-4" />}
              status="normal"
            />
            <StatCard
              title="Active Alerts"
              value={alertsList.length}
              subtitle="Sustained review threshold"
              icon={<AlertTriangle className="h-4 w-4" />}
              status={alertsList.length > 0 ? "critical" : "normal"}
            />
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Risk Donut Chart */}
            <div className="lg:col-span-5">
              <ChartContainer
                title="Welfare Risk Cohort Distribution"
                subtitle="Partitioned strictly into 3 locked operational bands"
                badge={
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#FAF9F5] border border-[#CFDDCE] text-[#2C5127] font-bold">
                    Aggregates Only
                  </span>
                }
              >
                {donutBuckets.length === 0 ? (
                  <p className="text-xs text-[#677766] py-12 text-center font-mono">
                    Operational cohort distribution: NOT_COMPUTED (Awaiting scheduled certification run)
                  </p>
                ) : (
                  <WsiDonutChart
                    buckets={donutBuckets}
                    totalPersonnel={totalCount ?? 0}
                  />
                )}
              </ChartContainer>
            </div>

            {/* Drivers Bar Chart */}
            <div className="lg:col-span-7">
              <ChartContainer
                title="Top Aggregate Operational Strain Drivers"
                subtitle="Weighted operational indicators driving unit strain"
                badge={
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#FAF9F5] border border-[#CFDDCE] text-[#2C5127] font-bold">
                    WSI 7-Factor
                  </span>
                }
              >
                {drivers.length === 0 ? (
                  <p className="text-xs text-[#677766] py-12 text-center font-mono">
                    Driver telemetry: NOT_COMPUTED (Awaiting completed leave/duty certification window)
                  </p>
                ) : (
                  <DriverBarChart drivers={drivers} />
                )}
              </ChartContainer>
            </div>
          </div>

          {/* Aggregate Trend Curve */}
          <ChartContainer
            title="Unit 90-Day Aggregate Workload Strain Index (EWMA Mean)"
            subtitle="Operational baseline trend smoothing short-term surges"
            footerNote="Command view aggregates preserve individual privacy. Raw psychometric data is isolated."
          >
            {trendPoints.length === 0 ? (
              <div className="p-12 text-center text-xs text-[#677766] font-mono bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                Trend telemetry: NOT_COMPUTED (Certified multi-day snapshot window accumulating under operational scheduler)
              </div>
            ) : (
              <WsiTrendChart data={trendPoints} />
            )}
          </ChartContainer>
        </div>
      )}

      {/* ─── Tab Content: Priority Roster & Operational Attention ────── */}
      {activeTab === "priority" && (
        <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h3 className="font-serif text-base font-bold text-[#182417]">
                Operational Attention &amp; Priority Roster ({priorityList.length})
              </h3>
              <p className="text-xs text-[#677766]">
                Personnel ranked by verified operational strain indicators. Strictly zero raw psychometric data.
              </p>
            </div>
            <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-[#FAF9F5] border border-[#CFDDCE] text-[#2C5127] font-bold">
              Privacy-Preserved View
            </span>
          </div>

          {priorityList.length === 0 ? (
            <div className="p-8 text-center text-xs text-[#677766] bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
              No elevated operational strain signals detected for this unit.
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {priorityList.map((person, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-0.5">
                    <div className="font-mono font-bold text-sm text-[#182417] flex items-center gap-2">
                      <span>{person.pseudo_id}</span>
                      <span className="text-[11px] font-normal text-[#677766]">
                        ({person.rank_or_grade})
                      </span>
                    </div>
                    <div className="text-[11px] text-[#677766]">
                      {person.role_title} • Status:{" "}
                      <span className="font-semibold text-[#182417]">{person.status}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="font-mono text-right text-xs">
                      <div>
                        WSI:{" "}
                        <strong>
                          {person.wsi !== null && person.wsi !== undefined ? person.wsi : person.wsi_status || "NOT_COMPUTED"}
                        </strong>
                      </div>
                      <div className="text-[10px] text-[#677766]">
                        Trend: {person.trend || "NOT_COMPUTED"}
                      </div>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleOpenStrainCard(person)}
                      icon={<Eye className="h-3.5 w-3.5" />}
                    >
                      Strain Card
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ─── Tab Content: Operational Alerts ─────────────────────────── */}
      {activeTab === "alerts" && (
        <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h3 className="font-serif text-base font-bold text-[#182417]">
                Operational Review Alerts ({alertsList.length})
              </h3>
              <p className="text-xs text-[#677766]">
                Sustained operational workload alerts requiring commander acknowledgment or resolution.
              </p>
            </div>
            <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-[#EAF1E9] border border-[#CFDDCE] text-[#2C5127] font-bold">
              Cooldown &amp; Deduplication Active
            </span>
          </div>

          {alertsList.length === 0 ? (
            <div className="p-12 text-center text-xs text-[#677766] bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
              Zero unresolved operational review alerts. Operational equilibrium verified.
            </div>
          ) : (
            <div className="space-y-3">
              {alertsList.map((alert) => (
                <div
                  key={alert.id}
                  className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-[#182417]">
                        {alert.alert_type || "HIGH_STRAIN_ALERT"}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border ${
                          alert.status === "OPEN"
                            ? "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]"
                            : alert.status === "ACKNOWLEDGED"
                            ? "bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]"
                            : "bg-[#ECFDF5] text-[#15803D] border-[#A7F3D0]"
                        }`}
                      >
                        {alert.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#3B4B3A]">
                      {alert.reason || "Operational strain sustained across consecutive duty observation window."}
                    </p>
                    <div className="text-[10px] font-mono text-[#677766]">
                      Created: {alert.created_at || "Recent"}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {alert.status === "OPEN" && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={actionInProgress === alert.id}
                        loading={actionInProgress === alert.id}
                        onClick={() => handleAcknowledgeAlert(alert.id)}
                        icon={<Check className="h-3.5 w-3.5" />}
                      >
                        Acknowledge
                      </Button>
                    )}
                    {alert.status !== "RESOLVED" && (
                      <Button
                        variant="primary"
                        size="sm"
                        disabled={actionInProgress === alert.id}
                        loading={actionInProgress === alert.id}
                        onClick={() => handleResolveAlert(alert.id)}
                        icon={<CheckCircle2 className="h-3.5 w-3.5" />}
                      >
                        Resolve
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ─── Tab Content: BALANCE Scenarios ──────────────────────────── */}
      {activeTab === "scenarios" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h3 className="font-serif text-base font-bold text-[#182417]">
                  BALANCE: Human-in-the-Loop Workload Alternatives
                </h3>
                <p className="text-xs text-[#677766]">
                  Transparent what-if roster proposals under hard operational constraints. Mandatory commander decision.
                </p>
              </div>
              <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-[#EAF1E9] border border-[#CFDDCE] text-[#2C5127] font-bold">
                Accept • Modify • Reject
              </span>
            </div>

            {scenariosList.length === 0 ? (
              <div className="p-12 text-center text-xs text-[#677766] bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                No pending roster balancing scenarios proposed. Workload remains balanced.
              </div>
            ) : (
              scenariosList.map((scenario) => (
                <div
                  key={scenario.id}
                  className="p-5 rounded-2xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-4 text-xs"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#CFDDCE] pb-3">
                    <div>
                      <div className="font-bold text-sm text-[#182417] font-serif">
                        {scenario.scenario_name}
                      </div>
                      <div className="text-[10px] font-mono text-[#677766]">
                        Optimizer: {scenario.optimizer_method} • Status:{" "}
                        <span className="font-bold text-[#2C5127]">{scenario.status}</span>
                      </div>
                    </div>

                    {scenario.status === "PROPOSED" && (
                      <div className="flex items-center gap-2">
                        <Button
                          variant="primary"
                          size="sm"
                          disabled={actionInProgress === scenario.id}
                          loading={actionInProgress === scenario.id}
                          onClick={() => handleDecideScenario(scenario.id, "ACCEPT", scenario.expected_revision)}
                          icon={<Check className="h-3.5 w-3.5" />}
                        >
                          Accept
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={actionInProgress === scenario.id}
                          onClick={() => handleDecideScenario(scenario.id, "MODIFY", scenario.expected_revision)}
                        >
                          Modify
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={actionInProgress === scenario.id}
                          onClick={() => handleDecideScenario(scenario.id, "REJECT", scenario.expected_revision)}
                          icon={<X className="h-3.5 w-3.5 text-[#B91C1C]" />}
                        >
                          Reject
                        </Button>
                      </div>
                    )}
                  </div>

                  {/* Before vs After Impact Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-xl bg-white border border-[#CFDDCE]">
                      <span className="text-[10px] text-[#677766] uppercase block font-mono">Night Ratio</span>
                      <div className="font-mono text-sm font-bold text-[#182417]">
                        {Math.round((scenario.before_metrics?.avg_night_ratio || 0) * 100)}% →{" "}
                        <span className="text-[#15803D]">
                          {Math.round((scenario.after_metrics?.avg_night_ratio || 0) * 100)}%
                        </span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-white border border-[#CFDDCE]">
                      <span className="text-[10px] text-[#677766] uppercase block font-mono">Min Rest (P10)</span>
                      <div className="font-mono text-sm font-bold text-[#182417]">
                        {scenario.before_metrics?.min_rest_hours_p10 || 0}h →{" "}
                        <span className="text-[#15803D]">
                          {scenario.after_metrics?.min_rest_hours_p10 || 0}h
                        </span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-white border border-[#CFDDCE]">
                      <span className="text-[10px] text-[#677766] uppercase block font-mono">Consecutive Days</span>
                      <div className="font-mono text-sm font-bold text-[#182417]">
                        {scenario.before_metrics?.avg_consecutive_duty_days || 0}d →{" "}
                        <span className="text-[#15803D]">
                          {scenario.after_metrics?.avg_consecutive_duty_days || 0}d
                        </span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-white border border-[#CFDDCE]">
                      <span className="text-[10px] text-[#677766] uppercase block font-mono">Staffing Coverage</span>
                      <div className="font-mono text-sm font-bold text-[#182417]">
                        {scenario.before_metrics?.staffing_coverage_percent || 0}% →{" "}
                        <span className="text-[#15803D]">
                          {scenario.after_metrics?.staffing_coverage_percent || 0}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Proposed Changes */}
                  {scenario.changes && scenario.changes.length > 0 && (
                    <div className="space-y-2">
                      <div className="font-semibold text-[#182417]">Proposed Rebalancing Adjustments:</div>
                      {scenario.changes.map((ch: any) => (
                        <div
                          key={ch.id}
                          className="p-3 rounded-lg bg-white border border-[#CFDDCE] flex flex-col sm:flex-row sm:items-center justify-between gap-2 font-mono text-[11px]"
                        >
                          <div>
                            <span className="font-bold text-[#2C5127]">{ch.personnel_pseudo_id}</span>: {ch.reason}
                          </div>
                          <span className="px-2 py-0.5 rounded bg-[#EAF1E9] text-[#2C5127] font-bold shrink-0">
                            {ch.change_type}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ─── Tab Content: Workload Analysis ──────────────────────────── */}
      {activeTab === "workload" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard
              title="Avg Weekly Duty Hours"
              value={workloadData?.avg_weekly_hours ? `${workloadData.avg_weekly_hours} hrs` : "NOT_COMPUTED"}
              subtitle="Governed standard: 48.0 hrs max"
              icon={<Clock className="h-4 w-4" />}
              status="normal"
            />
            <StatCard
              title="Night Shift Concentration"
              value={workloadData?.night_shift_percentage ? `${workloadData.night_shift_percentage}%` : "NOT_COMPUTED"}
              subtitle="Circadian recovery ceiling (<30%)"
              icon={<Activity className="h-4 w-4" />}
              status="normal"
            />
            <StatCard
              title="Consecutive Shift Mean"
              value={workloadData?.avg_consecutive_days ? `${workloadData.avg_consecutive_days} days` : "NOT_COMPUTED"}
              subtitle="Mandatory rest: Every 7 days"
              icon={<Calendar className="h-4 w-4" />}
              status="normal"
            />
          </div>

          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Workload Telemetry Governance
            </h3>
            <p className="text-xs text-[#3B4B3A] leading-relaxed">
              Workload aggregates are generated deterministically from certified duty and rest records. 
              Under AGENTS.md rules, missing or uncertified historical windows are displayed as NOT_COMPUTED 
              rather than interpolated into fabricated values.
            </p>
          </div>
        </div>
      )}

      {/* ─── Tab Content: Deployments ─────────────────────────────────── */}
      {activeTab === "deployments" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard
              title="Active Field Deployments"
              value={deployments?.active_field_count ?? "NOT_COMPUTED"}
              subtitle="Operational mission sectors"
              icon={<Briefcase className="h-4 w-4" />}
              status="normal"
            />
            <StatCard
              title="Static Garrison Posts"
              value={deployments?.static_base_count ?? "NOT_COMPUTED"}
              subtitle="Support & logistical maintenance"
              icon={<Users className="h-4 w-4" />}
              status="normal"
            />
            <StatCard
              title="Deployment Readiness"
              value={deployments?.coverage_percent ? `${deployments.coverage_percent}%` : "NOT_COMPUTED"}
              subtitle="Mission capability status"
              icon={<CheckCircle2 className="h-4 w-4" />}
              status="normal"
            />
          </div>

          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Deployment Record Verification
            </h3>
            <p className="text-xs text-[#3B4B3A] leading-relaxed">
              Deployment metrics require governed source CSV ingestion via the Admin portal and 
              subsequent scheduled pipeline runs. Individual deployment tracking maintains location 
              privacy boundaries.
            </p>
          </div>
        </div>
      )}

      {/* ─── Tab Content: Leave & Rest ───────────────────────────────── */}
      {activeTab === "leave" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Currently On Leave"
              value={leaveData?.on_leave_count ?? "NOT_COMPUTED"}
              subtitle="Sanctioned rotational leave"
              icon={<Calendar className="h-4 w-4" />}
              status="normal"
            />
            <StatCard
              title="Pending Approvals"
              value={leaveData?.pending_count ?? "NOT_COMPUTED"}
              subtitle="Under active command review"
              icon={<Clock className="h-4 w-4" />}
              status="neutral"
            />
            <StatCard
              title="Emergency / Medical"
              value={leaveData?.emergency_count ?? "NOT_COMPUTED"}
              subtitle="Compassionate leave records"
              icon={<AlertTriangle className="h-4 w-4" />}
              status="normal"
            />
            <StatCard
              title="Leave Fulfillment Rate"
              value={leaveData?.approval_rate ? `${leaveData.approval_rate}%` : "NOT_COMPUTED"}
              subtitle="30-day window metric"
              icon={<CheckCircle2 className="h-4 w-4" />}
              status="normal"
            />
          </div>

          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-3">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Leave &amp; Recovery Decision Rule
            </h3>
            <p className="text-xs text-[#3B4B3A] leading-relaxed">
              PRAHARI monitors leave pattern disruption without unilateral automated leave approvals. 
              The system alerts commanders when sustained duty pressure suppresses rotational recovery windows.
            </p>
          </div>
        </div>
      )}

      {/* ─── Tab Content: Risk Trends ────────────────────────────────── */}
      {activeTab === "trends" && (
        <div className="space-y-6">
          <ChartContainer
            title="Aggregate Unit Welfare Risk Trends (180-Day History)"
            subtitle="Smoothed EWMA trend curves tracking unit workload vs recovery baseline"
            footerNote="Risk bands strictly partitioned into LOW (0–39), MEDIUM (40–69), and HIGH (70–100)."
          >
            {trendPoints.length === 0 ? (
              <div className="p-12 text-center text-xs text-[#677766] font-mono bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
                Trend telemetry: NOT_COMPUTED (Certified multi-day snapshot window accumulating under operational scheduler)
              </div>
            ) : (
              <WsiTrendChart data={trendPoints} />
            )}
          </ChartContainer>
        </div>
      )}

      {/* ─── Strain Card Drawer ──────────────────────────────────────── */}
      <Drawer
        isOpen={Boolean(selectedStrainPerson)}
        onClose={() => {
          setSelectedStrainPerson(null);
          setStrainCardData(null);
        }}
        title={
          selectedStrainPerson
            ? `Operational Strain Card: ${selectedStrainPerson.pseudo_id}`
            : "Strain Card"
        }
        subtitle={
          selectedStrainPerson
            ? `${selectedStrainPerson.rank_or_grade} • ${selectedStrainPerson.role_title}`
            : undefined
        }
        badge={
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#FAF9F5] border border-[#CFDDCE] text-[#2C5127] font-bold">
            Authorized Commander View
          </span>
        }
      >
        <div className="space-y-5 text-xs">
          {strainCardLoading ? (
            <LoadingState title="Fetching operational strain metrics..." description="Retrieving authorized workload indicators" />
          ) : strainCardData ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 font-mono">
                <div className="p-3 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                  <span className="text-[10px] text-[#677766] uppercase block">WSI Score</span>
                  <span className="text-base font-bold text-[#182417]">
                    {strainCardData.wsi !== null && strainCardData.wsi !== undefined
                      ? strainCardData.wsi
                      : strainCardData.wsi_status || "NOT_COMPUTED"}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE]">
                  <span className="text-[10px] text-[#677766] uppercase block">Status</span>
                  <span className="text-base font-bold text-[#15803D]">
                    {strainCardData.status || "MONITORED"}
                  </span>
                </div>
              </div>

              {strainCardData.components && (
                <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-2">
                  <div className="font-semibold text-[#182417]">7-Factor WSI Components:</div>
                  <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                    <div>Duty Load (D): {strainCardData.components.duty_load ?? "—"}</div>
                    <div>Rest Deficit (R): {strainCardData.components.rest_deficit ?? "—"}</div>
                    <div>Circadian Night (N): {strainCardData.components.circadian_night ?? "—"}</div>
                    <div>Consecutive Shifts (C): {strainCardData.components.consecutive_shifts ?? "—"}</div>
                    <div>Leave Disruption (L): {strainCardData.components.leave_disruption ?? "—"}</div>
                    <div>Hazard Environment (H): {strainCardData.components.hazard_intensity ?? "—"}</div>
                  </div>
                </div>
              )}

              <div className="p-3 rounded-xl bg-[#EAF1E9] border border-[#CFDDCE] text-[11px] text-[#2C5127] leading-relaxed">
                Privacy Notice: This strain card presents operational workload and recovery factors only. 
                Raw private wellbeing questionnaire responses are strictly isolated and not disclosed to command.
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-[#677766] bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
              Strain card telemetry: Operational signals accumulating under scheduled pipeline.
            </div>
          )}
        </div>
      </Drawer>
    </div>
  );
}
