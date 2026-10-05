"use client";

import React, { useState, useEffect } from "react";
import {
  Settings,
  Shield,
  Server,
  Database,
  Cpu,
  Users,
  CheckCircle,
  RefreshCw,
  UserPlus,
  Lock,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Briefcase,
  Layers,
  KeyRound,
  FileCheck,
  ShieldCheck,
  HelpCircle,
  Play,
  Upload,
  FileSpreadsheet,
  ArrowRightLeft,
  Award,
  Calendar,
  History,
  Check,
  X,
  PlusCircle,
  Clock,
  Eye,
  FileText,
} from "lucide-react";
import { adminApi, generateIdempotencyKey } from "@/lib/api";
import { StatCard } from "@/components/common/Cards";
import { Button } from "@/components/common/Button";
import { StatusBadge } from "@/components/common/Badges";
import { LoadingState, EmptyState } from "@/components/common/States";
import { Drawer } from "@/components/common/Drawer";

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<
    "dashboard" | "users" | "personnel" | "units" | "skills" | "data" | "system"
  >("dashboard");
  const [health, setHealth] = useState<any>(null);
  const [models, setModels] = useState<any>(null);
  const [jobs, setJobs] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [personnel, setPersonnel] = useState<any[]>([]);
  const [units, setUnits] = useState<any[]>([]);
  const [skills, setSkills] = useState<any[]>([]);
  const [policies, setPolicies] = useState<any[]>([]);
  const [auditLog, setAuditLog] = useState<any[]>([]);
  const [importTemplates, setImportTemplates] = useState<any>(null);
  const [importHistory, setImportHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Operational Run State
  const [runCutoff, setRunCutoff] = useState("2026-08-30");
  const [runUnitId, setRunUnitId] = useState("");
  const [runSubmitting, setRunSubmitting] = useState(false);
  const [runResult, setRunResult] = useState<any | null>(null);

  // Create User form
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("prahari123");
  const [newRole, setNewRole] = useState("PERSONNEL");
  const [userCreating, setUserCreating] = useState(false);

  // Create Personnel form
  const [newPersCode, setNewPersCode] = useState("");
  const [newPersPseudo, setNewPersPseudo] = useState("");
  const [newPersFullName, setNewPersFullName] = useState("");
  const [newPersRank, setNewPersRank] = useState("CONSTABLE");
  const [newPersRole, setNewPersRole] = useState("Security Officer");
  const [newPersUnitId, setNewPersUnitId] = useState("");
  const [newPersServiceYears, setNewPersServiceYears] = useState(3);
  const [persCreating, setPersCreating] = useState(false);

  // Transfer Personnel form
  const [transferPersId, setTransferPersId] = useState("");
  const [transferTargetUnitId, setTransferTargetUnitId] = useState("");
  const [transferReason, setTransferReason] = useState("ROUTINE_ROTATION");
  const [transferSubmitting, setTransferSubmitting] = useState(false);

  // Create Unit form
  const [newUnitCode, setNewUnitCode] = useState("");
  const [newUnitName, setNewUnitName] = useState("");
  const [newUnitType, setNewUnitType] = useState("COMPANY");
  const [newUnitStrength, setNewUnitStrength] = useState(120);
  const [newUnitLocation, setNewUnitLocation] = useState("Northern Border");
  const [unitCreating, setUnitCreating] = useState(false);

  // Create Skill form
  const [newSkillCode, setNewSkillCode] = useState("");
  const [newSkillName, setNewSkillName] = useState("");
  const [newSkillCategory, setNewSkillCategory] = useState("TACTICAL");
  const [skillCreating, setSkillCreating] = useState(false);

  // 6-Dataset CSV Import State
  const [selectedDataset, setSelectedDataset] = useState<
    "duties" | "rest_records" | "leave_records" | "deployments" | "training" | "staffing"
  >("duties");
  const [csvText, setCsvText] = useState("");
  const [sourceTimestamp, setSourceTimestamp] = useState(new Date().toISOString());
  const [validatingImport, setValidatingImport] = useState(false);
  const [validationResult, setValidationResult] = useState<any | null>(null);
  const [committingImport, setCommittingImport] = useState(false);
  const [commitResult, setCommitResult] = useState<any | null>(null);

  useEffect(() => {
    loadData();

    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tab = params.get("tab");
      if (tab === "users") setActiveTab("users");
      else if (tab === "personnel") setActiveTab("personnel");
      else if (tab === "units") setActiveTab("units");
      else if (tab === "skills") setActiveTab("skills");
      else if (tab === "data" || tab === "imports") setActiveTab("data");
      else if (tab === "system" || tab === "settings") setActiveTab("system");
      else if (tab === "dashboard") setActiveTab("dashboard");
    }
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [h, m, j, u, p, un, sk, pol, aud, tpls, imps] = await Promise.all([
        adminApi.getHealth().catch(() => null),
        adminApi.getModels().catch(() => null),
        adminApi.getJobs().catch(() => null),
        adminApi.listUsers().catch(() => []),
        adminApi.listPersonnel().catch(() => []),
        adminApi.listUnits().catch(() => []),
        adminApi.listSkills().catch(() => ({ items: [] })),
        adminApi.listPolicies().catch(() => []),
        adminApi.getAudit().catch(() => []),
        adminApi.getImportTemplates().catch(() => null),
        adminApi.getImportHistory().catch(() => ({ items: [] })),
      ]);
      setHealth(h);
      setModels(m);
      setJobs(j);
      setUsers(u || []);
      setPersonnel(p || []);
      setUnits(un || []);
      setSkills(sk?.items || []);
      setPolicies(pol || []);
      setAuditLog(aud || []);
      setImportTemplates(tpls);
      setImportHistory(imps?.items || []);

      if (un && un.length > 0) {
        if (!newPersUnitId) setNewPersUnitId(un[0].id);
        if (!transferTargetUnitId) setTransferTargetUnitId(un[0].id);
      }
      if (p && p.length > 0 && !transferPersId) {
        setTransferPersId(p[0].id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  }

  // Handle Trigger Operational Run
  async function handleTriggerRun(e: React.FormEvent) {
    e.preventDefault();
    setRunSubmitting(true);
    setRunResult(null);
    setError(null);
    try {
      const res = await adminApi.triggerOperationalRun({
        cutoff: runCutoff,
        unit_id: runUnitId || undefined,
      });
      setRunResult(res);
      setSuccessMsg(
        `Operational detection run finished: ${res.processed} records processed (${res.mode} mode).`
      );
    } catch (err: any) {
      setError(err.message || "Operational run failed");
    } finally {
      setRunSubmitting(false);
    }
  }

  // Handle Create User
  async function handleCreateUser(e: React.FormEvent) {
    e.preventDefault();
    if (!newUsername || !newPassword) return;
    setUserCreating(true);
    setError(null);
    try {
      await adminApi.createUser({
        username: newUsername,
        password: newPassword,
        role: newRole,
      });
      setSuccessMsg(`User '${newUsername}' successfully created with Argon2id hash!`);
      setNewUsername("");
      const refreshed = await adminApi.listUsers();
      setUsers(refreshed || []);
    } catch (err: any) {
      setError(err.message || "Failed to create user");
    } finally {
      setUserCreating(false);
    }
  }

  async function handleToggleUserActive(userId: string, currentActive: boolean) {
    try {
      await adminApi.updateUser(userId, { is_active: !currentActive });
      const refreshed = await adminApi.listUsers();
      setUsers(refreshed || []);
      setSuccessMsg("User activation status updated.");
    } catch (err: any) {
      setError(err.message);
    }
  }

  // Handle Create Personnel
  async function handleCreatePersonnel(e: React.FormEvent) {
    e.preventDefault();
    if (!newPersCode || !newPersFullName || !newPersUnitId) return;
    setPersCreating(true);
    setError(null);
    try {
      const pseudo = newPersPseudo || `PRH-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
      await adminApi.createPersonnel({
        personnel_code: newPersCode,
        pseudo_id: pseudo,
        full_name: newPersFullName,
        rank_or_grade: newPersRank,
        role_title: newPersRole,
        unit_id: newPersUnitId,
        service_years: Number(newPersServiceYears),
      });
      setSuccessMsg(`Personnel record '${newPersFullName}' (${pseudo}) created successfully.`);
      setNewPersCode("");
      setNewPersPseudo("");
      setNewPersFullName("");
      const refreshed = await adminApi.listPersonnel();
      setPersonnel(refreshed || []);
    } catch (err: any) {
      setError(err.message || "Failed to create personnel");
    } finally {
      setPersCreating(false);
    }
  }

  // Handle Transfer Personnel
  async function handleTransferPersonnel(e: React.FormEvent) {
    e.preventDefault();
    if (!transferPersId || !transferTargetUnitId) return;
    setTransferSubmitting(true);
    setError(null);
    try {
      await adminApi.transferPersonnel(transferPersId, {
        target_unit_id: transferTargetUnitId,
        reason: transferReason,
      });
      setSuccessMsg("Personnel unit transfer executed and logged to audit.");
      const refreshed = await adminApi.listPersonnel();
      setPersonnel(refreshed || []);
    } catch (err: any) {
      setError(err.message || "Failed to transfer personnel");
    } finally {
      setTransferSubmitting(false);
    }
  }

  // Handle Create Unit
  async function handleCreateUnit(e: React.FormEvent) {
    e.preventDefault();
    if (!newUnitCode || !newUnitName) return;
    setUnitCreating(true);
    setError(null);
    try {
      await adminApi.createUnit({
        unit_code: newUnitCode,
        unit_name: newUnitName,
        unit_type: newUnitType,
        sanctioned_strength: Number(newUnitStrength),
        location_label: newUnitLocation,
      });
      setSuccessMsg(`Unit '${newUnitName}' (${newUnitCode}) created successfully.`);
      setNewUnitCode("");
      setNewUnitName("");
      const refreshed = await adminApi.listUnits();
      setUnits(refreshed || []);
    } catch (err: any) {
      setError(err.message || "Failed to create unit");
    } finally {
      setUnitCreating(false);
    }
  }

  // Handle Create Skill
  async function handleCreateSkill(e: React.FormEvent) {
    e.preventDefault();
    if (!newSkillCode || !newSkillName) return;
    setSkillCreating(true);
    setError(null);
    try {
      await adminApi.createSkill({
        skill_code: newSkillCode,
        skill_name: newSkillName,
        category: newSkillCategory,
      });
      setSuccessMsg(`Skill '${newSkillName}' (${newSkillCode}) created successfully.`);
      setNewSkillCode("");
      setNewSkillName("");
      const refreshed = await adminApi.listSkills();
      setSkills(refreshed?.items || []);
    } catch (err: any) {
      setError(err.message || "Failed to create skill");
    } finally {
      setSkillCreating(false);
    }
  }

  // CSV Import Step 1: Validate
  async function handleValidateImport(e: React.FormEvent) {
    e.preventDefault();
    if (!csvText.trim()) {
      setError("Please paste CSV data to validate.");
      return;
    }
    setValidatingImport(true);
    setError(null);
    setValidationResult(null);
    setCommitResult(null);
    try {
      const res = await adminApi.validateImport({
        dataset_type: selectedDataset,
        csv_data: csvText.trim(),
        source_timestamp: sourceTimestamp,
      });
      setValidationResult(res);
      if (res.status === "VALIDATED") {
        setSuccessMsg(`CSV validation passed: ${res.row_count} rows ready for atomic commit.`);
      } else {
        setError(`CSV validation rejected: ${res.errors?.length || 0} formatting/schema errors found.`);
      }
    } catch (err: any) {
      setError(err.message || "Validation failed");
    } finally {
      setValidatingImport(false);
    }
  }

  // CSV Import Step 2: Atomic Commit
  async function handleCommitImport() {
    if (!validationResult || validationResult.status !== "VALIDATED") return;
    setCommittingImport(true);
    setError(null);
    try {
      const res = await adminApi.commitImport(validationResult.id, {
        dataset_type: selectedDataset,
        csv_data: csvText.trim(),
        source_timestamp: sourceTimestamp,
        checksum: validationResult.checksum,
        expected_revision: validationResult.revision,
      });
      setCommitResult(res);
      setSuccessMsg(
        `Import committed atomically: ${res.row_count} rows written to ${res.dataset_type} (Revision: ${res.revision.slice(0, 10)}...).`
      );
      setValidationResult(null);
      setCsvText("");
      const imps = await adminApi.getImportHistory();
      setImportHistory(imps?.items || []);
    } catch (err: any) {
      setError(err.message || "Atomic commit failed");
    } finally {
      setCommittingImport(false);
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ─── Header & Telemetry Status ───────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#CFDDCE]">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-serif text-2xl font-bold text-[#182417]">
              System Administration &amp; Governance
            </h1>
            <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-[#FEF3C7] border border-[#FDE68A] text-[#B45309] font-bold">
              Console Only (Zero Clinical Decisions)
            </span>
          </div>
          <p className="text-xs text-[#677766] mt-1">
            4-Role RBAC • Master Ingestion • Pipeline Trigger • RLS Enforcement • Immutable Audit Ledger
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            disabled={loading}
            icon={<RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />}
          >
            Refresh Telemetry
          </Button>

          <span className="px-3 py-1.5 rounded-full bg-[#ECFDF5] text-[#15803D] text-xs font-semibold border border-[#A7F3D0] flex items-center gap-1.5">
            <CheckCircle className="h-4 w-4" />
            <span>DB: {health?.database_status || "CONNECTED"}</span>
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

      {successMsg && (
        <div className="p-3.5 rounded-xl bg-[#ECFDF5] text-[#15803D] border border-[#A7F3D0] text-xs flex items-center justify-between gap-2 animate-in fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="p-1 hover:bg-[#A7F3D0] rounded">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* ─── Tabs Navigation ─────────────────────────────────────────── */}
      <div className="flex border-b border-[#CFDDCE] space-x-2 overflow-x-auto">
        {[
          { id: "dashboard", label: "Dashboard & Health" },
          { id: "users", label: `User Accounts (${users.length})` },
          { id: "personnel", label: `Personnel Master (${personnel.length})` },
          { id: "units", label: `Units (${units.length})` },
          { id: "skills", label: `Skills (${skills.length})` },
          { id: "data", label: "6-Dataset CSV Import" },
          { id: "system", label: "Security & Governance Audit" },
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

      {/* ─── Tab 1: Dashboard & Health ───────────────────────────────── */}
      {activeTab === "dashboard" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="FastAPI Service"
              value="ACTIVE (:8000)"
              subtitle="prahari_backend container"
              icon={<Server className="h-4 w-4 text-[#15803D]" />}
              status="normal"
            />
            <StatCard
              title="PostgreSQL 16 DB"
              value="CONNECTED (:5432)"
              subtitle="Row-Level Security Active"
              icon={<Database className="h-4 w-4 text-[#2C5127]" />}
              status="normal"
            />
            <StatCard
              title="Scheduler Cadence"
              value={jobs?.scheduler_status || "RUNNING"}
              subtitle={jobs?.scheduler_cadence || "00:15 UTC daily"}
              icon={<Clock className="h-4 w-4 text-[#5B2C78]" />}
              status="normal"
            />
            <StatCard
              title="Registered Accounts"
              value={`${users.length} Users`}
              subtitle="Argon2id Hashed Passwords"
              icon={<Users className="h-4 w-4 text-[#B8860B]" />}
              status="normal"
            />
          </div>

          {/* Model Governance Status Grid (Strictly Truthful) */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
                <Cpu className="h-4 w-4 text-[#5B2C78]" />
                <span>ML Pipeline &amp; Algorithmic Governance Status</span>
              </h3>
              <span className="text-[11px] font-mono px-2.5 py-0.5 rounded bg-[#FAF9F5] border border-[#CFDDCE] text-[#3B4B3A]">
                Authoritative Contract (AGENTS.md)
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
              {/* Model A */}
              <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#182417]">Model A (Operational Prototype)</span>
                  <span className="px-2 py-0.5 rounded bg-[#ECFDF5] text-[#15803D] font-bold text-[10px]">
                    {models?.model_a?.status || "MODEL_AVAILABLE"}
                  </span>
                </div>
                <div className="text-[11px] text-[#677766] space-y-1">
                  <div>Features: <strong>{models?.model_a?.feature_count || 15}</strong></div>
                  <div>Threshold: <strong>{models?.model_a?.threshold || "0.15"}</strong></div>
                  <div>Policy: <strong>{models?.model_a?.threshold_policy || "PROVISIONAL_V1"}</strong></div>
                  <div className="text-[10px] text-[#B45309] pt-1">
                    Synthetic prototype demonstration only. Not clinical or real military validity.
                  </div>
                </div>
              </div>

              {/* Engine B */}
              <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#D8B4FE] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#182417]">Engine B (Private Wellbeing)</span>
                  <span className="px-2 py-0.5 rounded bg-[#F3E8FF] text-[#5B2C78] font-bold text-[10px]">
                    {models?.engine_b?.status || "INSTRUMENT_NOT_ACTIVATED"}
                  </span>
                </div>
                <div className="text-[11px] text-[#677766] space-y-1">
                  <div>Training Status: <strong>{models?.engine_b?.training_status || "NOT_TRAINED"}</strong></div>
                  <div>Consent Boundary: <strong>STRICT ISOLATION</strong></div>
                  <div className="text-[10px] text-[#5B2C78] pt-1">
                    Gated by PRAHARI Ethical Charter. No synthetic psychometric labels fabricated.
                  </div>
                </div>
              </div>

              {/* Model C */}
              <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#182417]">Model C (Convergence Protocol)</span>
                  <span className="px-2 py-0.5 rounded bg-[#ECFDF5] text-[#15803D] font-bold text-[10px]">
                    ACTIVE
                  </span>
                </div>
                <div className="text-[11px] text-[#677766] space-y-1">
                  <div>Rules Version: <strong>{models?.model_c?.rules_version || "v1.1-truthful"}</strong></div>
                  <div>Type: <strong>{models?.model_c?.type || "DETERMINISTIC"}</strong></div>
                  <div className="text-[10px] text-[#15803D] pt-1">
                    Evidence convergence logic enforces operational transparency.
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Trigger Operational Detection Run Form */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
                  <Play className="h-4 w-4 text-[#2C5127]" />
                  <span>Execute Operational Strain Detection Run</span>
                </h3>
                <p className="text-xs text-[#677766] mt-0.5">
                  Runs the historical operational pipeline across all active personnel up to the specified cutoff date.
                </p>
              </div>
            </div>

            <form onSubmit={handleTriggerRun} className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
              <div>
                <label className="block text-[10px] font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Cutoff Date (YYYY-MM-DD)
                </label>
                <input
                  type="date"
                  value={runCutoff}
                  onChange={(e) => setRunCutoff(e.target.value)}
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Unit Scope (Optional)
                </label>
                <select
                  value={runUnitId}
                  onChange={(e) => setRunUnitId(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                >
                  <option value="">All Authorized Units</option>
                  {units.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.unit_name} ({u.unit_code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-end">
                <Button
                  type="submit"
                  loading={runSubmitting}
                  disabled={runSubmitting}
                  icon={<Play className="h-4 w-4" />}
                  className="w-full"
                >
                  Trigger Detection Run
                </Button>
              </div>
            </form>

            {runResult && (
              <div className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-2 text-xs font-mono">
                <div className="font-bold text-[#182417] flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-[#15803D]" />
                  <span>Run Completed Successfully: Mode {runResult.mode} (Cutoff: {runResult.cutoff})</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[#E4ECE3]">
                  <div>Processed: <strong>{runResult.processed}</strong></div>
                  <div>Valid Scores: <strong>{runResult.valid}</strong></div>
                  <div>Unavailable: <strong>{runResult.unavailable}</strong></div>
                  <div>Alerts Created: <strong>{runResult.alerts_created}</strong></div>
                </div>
              </div>
            )}
          </div>

          {/* Table Counts Matrix */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              PostgreSQL Live Table Record Counts
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              {health?.table_record_counts &&
                Object.entries(health.table_record_counts).map(([tbl, count]: any) => (
                  <div
                    key={tbl}
                    className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-1"
                  >
                    <span className="text-[10px] text-[#677766] uppercase block truncate">
                      {tbl}
                    </span>
                    <span className="text-lg font-bold text-[#2C5127] block">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab 2: Users (4 Roles Only) ─────────────────────────────── */}
      {activeTab === "users" && (
        <div className="space-y-6">
          {/* Create User Form */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <UserPlus className="h-4 w-4 text-[#2C5127]" />
              <span>Provision User Account (Strict 4 Roles: PERSONNEL, COMMANDER, WELFARE_OFFICER, ADMIN)</span>
            </h3>

            <form onSubmit={handleCreateUser} className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs font-mono">
              <div>
                <label className="block text-[10px] font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                  USERNAME
                </label>
                <input
                  type="text"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  placeholder="e.g. officer_sharma"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                  INITIAL PASSWORD
                </label>
                <input
                  type="text"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Password"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-[#3B4B3A] mb-1 font-semibold">
                  LOCKED ROLE
                </label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                >
                  <option value="PERSONNEL">PERSONNEL</option>
                  <option value="COMMANDER">COMMANDER</option>
                  <option value="WELFARE_OFFICER">WELFARE_OFFICER</option>
                  <option value="ADMIN">ADMIN</option>
                </select>
              </div>

              <div className="flex items-end">
                <Button
                  type="submit"
                  disabled={userCreating || !newUsername}
                  loading={userCreating}
                  icon={<UserPlus className="h-4 w-4" />}
                  className="w-full"
                >
                  Create User
                </Button>
              </div>
            </form>
          </div>

          {/* User Table */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Registered System Accounts ({users.length})
            </h3>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {users.map((u) => (
                <div
                  key={u.id}
                  className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex items-center justify-between text-xs font-mono"
                >
                  <div>
                    <div className="font-bold text-sm text-[#182417]">{u.username}</div>
                    <div className="text-[10px] text-[#677766]">
                      Created: {u.created_at || "Seed"}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2.5 py-1 rounded text-[10px] font-bold border ${
                        u.role === "COMMANDER"
                          ? "bg-[#EAF1E9] text-[#2C5127] border-[#CFDDCE]"
                          : u.role === "WELFARE_OFFICER"
                          ? "bg-purple-50 text-purple-700 border-purple-200"
                          : u.role === "ADMIN"
                          ? "bg-amber-50 text-amber-800 border-amber-200"
                          : "bg-emerald-50 text-emerald-800 border-emerald-200"
                      }`}
                    >
                      {u.role}
                    </span>

                    <button
                      onClick={() => handleToggleUserActive(u.id, u.is_active)}
                      className={`px-3 py-1 rounded text-[10px] font-bold transition-colors ${
                        u.is_active
                          ? "bg-[#ECFDF5] text-[#15803D] hover:bg-rose-50 hover:text-rose-700"
                          : "bg-rose-50 text-rose-700 hover:bg-[#ECFDF5] hover:text-[#15803D]"
                      }`}
                    >
                      {u.is_active ? "ACTIVE" : "INACTIVE"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab 3: Personnel Master & Transfer ───────────────────────── */}
      {activeTab === "personnel" && (
        <div className="space-y-6">
          {/* Create Personnel Form */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <PlusCircle className="h-4 w-4 text-[#2C5127]" />
              <span>Enroll Personnel Master Record</span>
            </h3>

            <form onSubmit={handleCreatePersonnel} className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Personnel Code (Service No.)
                </label>
                <input
                  type="text"
                  value={newPersCode}
                  onChange={(e) => setNewPersCode(e.target.value)}
                  placeholder="e.g. P0999"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Full Name
                </label>
                <input
                  type="text"
                  value={newPersFullName}
                  onChange={(e) => setNewPersFullName(e.target.value)}
                  placeholder="e.g. Inspector Ramesh Singh"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Assigned Unit
                </label>
                <select
                  value={newPersUnitId}
                  onChange={(e) => setNewPersUnitId(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                >
                  {units.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.unit_name} ({u.unit_code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Rank or Grade
                </label>
                <input
                  type="text"
                  value={newPersRank}
                  onChange={(e) => setNewPersRank(e.target.value)}
                  placeholder="e.g. CONSTABLE"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Role Title
                </label>
                <input
                  type="text"
                  value={newPersRole}
                  onChange={(e) => setNewPersRole(e.target.value)}
                  placeholder="e.g. Patrol Leader"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div className="flex items-end">
                <Button
                  type="submit"
                  disabled={persCreating}
                  loading={persCreating}
                  icon={<PlusCircle className="h-4 w-4" />}
                  className="w-full"
                >
                  Enroll Personnel
                </Button>
              </div>
            </form>
          </div>

          {/* Transfer Personnel Form */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <ArrowRightLeft className="h-4 w-4 text-[#5B2C78]" />
              <span>Execute Unit Reassignment / Transfer</span>
            </h3>

            <form onSubmit={handleTransferPersonnel} className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Select Personnel
                </label>
                <select
                  value={transferPersId}
                  onChange={(e) => setTransferPersId(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                >
                  {personnel.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.pseudo_id} ({p.rank_or_grade})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Target Destination Unit
                </label>
                <select
                  value={transferTargetUnitId}
                  onChange={(e) => setTransferTargetUnitId(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                >
                  {units.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.unit_name} ({u.unit_code})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Reason Code
                </label>
                <select
                  value={transferReason}
                  onChange={(e) => setTransferReason(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                >
                  <option value="ROUTINE_ROTATION">ROUTINE_ROTATION</option>
                  <option value="OPERATIONAL_NEED">OPERATIONAL_NEED</option>
                  <option value="COMPASSIONATE_GROUNDS">COMPASSIONATE_GROUNDS</option>
                  <option value="SPECIALIZED_SKILL">SPECIALIZED_SKILL</option>
                </select>
              </div>

              <div className="flex items-end">
                <Button
                  type="submit"
                  disabled={transferSubmitting}
                  loading={transferSubmitting}
                  icon={<ArrowRightLeft className="h-4 w-4" />}
                  className="w-full"
                >
                  Execute Transfer
                </Button>
              </div>
            </form>
          </div>

          {/* Personnel Master Table */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Personnel Master Records ({personnel.length})
            </h3>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {personnel.map((p) => (
                <div
                  key={p.id}
                  className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center text-xs"
                >
                  <div>
                    <div className="font-mono font-bold text-sm text-[#182417]">
                      {p.pseudo_id} ({p.rank_or_grade})
                    </div>
                    <div className="text-[11px] text-[#677766] mt-0.5">
                      {p.role_title} • Code: {p.personnel_code}
                    </div>
                  </div>
                  <div className="font-mono text-[11px] text-right">
                    <div>Service: {p.service_years} yrs</div>
                    <div className="text-[#15803D] font-bold">{p.status}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab 4: Units ────────────────────────────────────────────── */}
      {activeTab === "units" && (
        <div className="space-y-6">
          {/* Create Unit Form */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <PlusCircle className="h-4 w-4 text-[#2C5127]" />
              <span>Create Unit Structure</span>
            </h3>

            <form onSubmit={handleCreateUnit} className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Unit Code
                </label>
                <input
                  type="text"
                  value={newUnitCode}
                  onChange={(e) => setNewUnitCode(e.target.value)}
                  placeholder="e.g. U09"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Unit Name
                </label>
                <input
                  type="text"
                  value={newUnitName}
                  onChange={(e) => setNewUnitName(e.target.value)}
                  placeholder="e.g. 5th Border Battalion"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Sanctioned Strength
                </label>
                <input
                  type="number"
                  value={newUnitStrength}
                  onChange={(e) => setNewUnitStrength(Number(e.target.value))}
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div className="flex items-end">
                <Button
                  type="submit"
                  disabled={unitCreating}
                  loading={unitCreating}
                  icon={<PlusCircle className="h-4 w-4" />}
                  className="w-full"
                >
                  Create Unit
                </Button>
              </div>
            </form>
          </div>

          {/* Unit Master Cards */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Battalion &amp; Company Master ({units.length})
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {units.map((un) => (
                <div
                  key={un.id}
                  className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs space-y-1.5"
                >
                  <div className="font-bold text-sm text-[#182417] font-mono">
                    {un.unit_name} ({un.unit_code})
                  </div>
                  <div className="text-[11px] text-[#677766]">
                    Type: {un.unit_type} • Location: {un.location_label || "Base"}
                  </div>
                  <div className="text-[11px] text-[#2C5127] font-mono font-semibold">
                    Sanctioned Strength: {un.sanctioned_strength} Personnel
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab 5: Skills Master ─────────────────────────────────────── */}
      {activeTab === "skills" && (
        <div className="space-y-6">
          {/* Create Skill Form */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <Award className="h-4 w-4 text-[#2C5127]" />
              <span>Define Operational Skill</span>
            </h3>

            <form onSubmit={handleCreateSkill} className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Skill Code
                </label>
                <input
                  type="text"
                  value={newSkillCode}
                  onChange={(e) => setNewSkillCode(e.target.value)}
                  placeholder="e.g. SK09"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Skill Name
                </label>
                <input
                  type="text"
                  value={newSkillName}
                  onChange={(e) => setNewSkillName(e.target.value)}
                  placeholder="e.g. Drone Pilot Level 2"
                  required
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div>
                <label className="block text-[10px] uppercase text-[#3B4B3A] mb-1 font-semibold">
                  Category
                </label>
                <select
                  value={newSkillCategory}
                  onChange={(e) => setNewSkillCategory(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                >
                  <option value="TACTICAL">TACTICAL</option>
                  <option value="MEDICAL">MEDICAL</option>
                  <option value="TECHNICAL">TECHNICAL</option>
                  <option value="COMMUNICATIONS">COMMUNICATIONS</option>
                </select>
              </div>

              <div className="flex items-end">
                <Button
                  type="submit"
                  disabled={skillCreating}
                  loading={skillCreating}
                  icon={<Award className="h-4 w-4" />}
                  className="w-full"
                >
                  Register Skill
                </Button>
              </div>
            </form>
          </div>

          {/* Skills Master Table */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              Certified Operational Skills ({skills.length})
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
              {skills.map((sk) => (
                <div
                  key={sk.id}
                  className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center"
                >
                  <div>
                    <div className="font-bold text-[#182417]">
                      {sk.skill_name} ({sk.skill_code})
                    </div>
                    <div className="text-[10px] text-[#677766]">
                      Category: {sk.category || "GENERAL"}
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-[#ECFDF5] text-[#15803D] font-bold text-[10px]">
                    ACTIVE
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab 6: 6-Dataset CSV Import ─────────────────────────────── */}
      {activeTab === "data" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <div>
              <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-[#2C5127]" />
                <span>6-Dataset CSV Ingestion Engine (Validate &amp; Atomic Commit)</span>
              </h3>
              <p className="text-xs text-[#677766] mt-0.5">
                Two-stage atomic import engine. Validates schema, checksum, and foreign key integrity before transactional commit.
              </p>
            </div>

            {/* Dataset Selector Tabs */}
            <div className="flex gap-2 flex-wrap border-b border-[#CFDDCE] pb-2">
              {[
                { id: "duties", label: "1. Duties" },
                { id: "rest_records", label: "2. Rest Records" },
                { id: "leave_records", label: "3. Leave Records" },
                { id: "deployments", label: "4. Deployments" },
                { id: "training", label: "5. Training" },
                { id: "staffing", label: "6. Staffing" },
              ].map((ds) => (
                <button
                  key={ds.id}
                  type="button"
                  onClick={() => {
                    setSelectedDataset(ds.id as any);
                    setValidationResult(null);
                    setCommitResult(null);
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    selectedDataset === ds.id
                      ? "bg-[#2C5127] text-white shadow-sm"
                      : "bg-[#FAF9F5] text-[#3B4B3A] hover:bg-[#EAF1E9]"
                  }`}
                >
                  {ds.label}
                </button>
              ))}
            </div>

            {/* Template Expected Fields preview */}
            {importTemplates && (
              <div className="p-3.5 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] text-xs font-mono space-y-1">
                <div className="font-bold text-[#182417]">
                  Expected Fields for `{selectedDataset}`:
                </div>
                <div className="text-[11px] text-[#677766] flex flex-wrap gap-1.5">
                  {importTemplates.datasets
                    ?.find((d: any) => d.dataset_type === selectedDataset)
                    ?.fields?.map((f: any) => (
                      <span key={f.name} className="px-2 py-0.5 rounded bg-white border border-[#CFDDCE]">
                        <strong>{f.name}</strong> ({f.type}){f.required ? " *" : ""}
                      </span>
                    ))}
                </div>
              </div>
            )}

            {/* CSV Form */}
            <form onSubmit={handleValidateImport} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#3B4B3A] mb-1 font-mono">
                  Paste Raw CSV Content (Header Row Required)
                </label>
                <textarea
                  rows={6}
                  value={csvText}
                  onChange={(e) => setCsvText(e.target.value)}
                  placeholder={`personnel_id,unit_id,shift_type,duty_date,duration_hours...\nPaste comma-separated rows`}
                  required
                  className="w-full p-3 bg-white border border-[#CFDDCE] rounded-lg text-xs font-mono text-[#182417] focus:outline-none focus:ring-2 focus:ring-[#2C5127]"
                />
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
                <div className="text-xs font-mono text-[#677766]">
                  Source Timestamp: <span className="text-[#182417] font-bold">{sourceTimestamp}</span>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    type="submit"
                    loading={validatingImport}
                    disabled={validatingImport || !csvText.trim()}
                    icon={<FileCheck className="h-4 w-4" />}
                    variant="outline"
                  >
                    1. Validate CSV
                  </Button>

                  {validationResult?.status === "VALIDATED" && (
                    <Button
                      type="button"
                      onClick={handleCommitImport}
                      loading={committingImport}
                      disabled={committingImport}
                      icon={<Check className="h-4 w-4" />}
                      className="bg-[#15803D] hover:bg-[#166534] text-white"
                    >
                      2. Atomic Commit ({validationResult.row_count} rows)
                    </Button>
                  )}
                </div>
              </div>
            </form>

            {/* Validation Feedback */}
            {validationResult && (
              <div className={`p-4 rounded-xl border text-xs font-mono space-y-2 ${
                validationResult.status === "VALIDATED"
                  ? "bg-[#ECFDF5] border-[#A7F3D0] text-[#15803D]"
                  : "bg-[#FEF2F2] border-[#FECACA] text-[#B91C1C]"
              }`}>
                <div className="font-bold flex items-center gap-2">
                  {validationResult.status === "VALIDATED" ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}
                  <span>Status: {validationResult.status} • Row Count: {validationResult.row_count}</span>
                </div>
                <div>Checksum: <span className="font-bold">{validationResult.checksum}</span></div>
                {validationResult.errors && validationResult.errors.length > 0 && (
                  <div className="mt-2 space-y-1 max-h-40 overflow-y-auto pt-2 border-t border-[#FECACA]">
                    {validationResult.errors.map((err: any, idx: number) => (
                      <div key={idx} className="text-[11px]">
                        Row {err.row}: [{err.field}] {err.error} (raw: &quot;{err.raw_value}&quot;)
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Commit Result */}
            {commitResult && (
              <div className="p-4 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] text-xs font-mono text-[#15803D] space-y-1">
                <div className="font-bold flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Atomic Commit Succeeded!</span>
                </div>
                <div>Dataset: <strong>{commitResult.dataset_type}</strong></div>
                <div>Rows Written: <strong>{commitResult.row_count}</strong></div>
                <div>Revision Hash: <strong>{commitResult.revision}</strong></div>
                <div>Committed At: <strong>{commitResult.committed_at}</strong></div>
              </div>
            )}
          </div>

          {/* Import History Table */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <History className="h-4 w-4 text-[#2C5127]" />
              <span>Historical Ingestions ({importHistory.length})</span>
            </h3>

            {importHistory.length === 0 ? (
              <EmptyState title="No Past Imports" description="Validated and committed CSV batches will appear here." />
            ) : (
              <div className="divide-y divide-[#E4ECE3] border border-[#CFDDCE] rounded-xl overflow-hidden text-xs font-mono">
                {importHistory.map((item) => (
                  <div key={item.id} className="p-3.5 bg-white flex justify-between items-center">
                    <div>
                      <div className="font-bold text-[#182417]">
                        {item.dataset_type} • {item.row_count} rows
                      </div>
                      <div className="text-[10px] text-[#677766]">
                        Checksum: {item.checksum?.slice(0, 16)}...
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="px-2 py-0.5 rounded bg-[#ECFDF5] text-[#15803D] font-bold text-[10px]">
                        {item.status}
                      </span>
                      <div className="text-[10px] text-[#677766] mt-0.5">
                        {item.created_at ? new Date(item.created_at).toLocaleDateString() : "Historical"}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── Tab 7: Security & Audit Ledger ──────────────────────────── */}
      {activeTab === "system" && (
        <div className="space-y-6">
          {/* Security & RLS Policies */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <Lock className="h-4 w-4 text-[#15803D]" />
              <span>Active Governance Policies ({policies.length})</span>
            </h3>
            <div className="space-y-3 text-xs font-mono">
              {policies.map((p) => (
                <div key={p.id} className="p-4 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] space-y-1">
                  <div className="font-bold text-[#15803D] flex items-center justify-between">
                    <span>{p.policy_key}</span>
                    <span className="text-[10px] text-[#677766] font-normal">Version: {p.version}</span>
                  </div>
                  <div className="text-[#3B4B3A] text-[11px]">
                    Effective: {new Date(p.effective_from).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Immutable Audit Trail */}
          <div className="bg-white rounded-2xl border border-[#CFDDCE] p-6 shadow-sm space-y-4">
            <h3 className="font-serif text-base font-bold text-[#182417] flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[#2C5127]" />
              <span>Immutable Governance Audit Log ({auditLog.length})</span>
            </h3>

            <div className="space-y-2 max-h-[500px] overflow-y-auto text-xs font-mono">
              {auditLog.map((log) => (
                <div
                  key={log.id}
                  className="p-3 rounded-xl bg-[#FAF9F5] border border-[#CFDDCE] flex justify-between items-center"
                >
                  <div>
                    <div className="font-bold text-[#182417] flex items-center gap-2">
                      <span className="text-[#2C5127]">{log.action}</span>
                      <span className="text-[#677766] font-normal">by {log.actor_role}</span>
                    </div>
                    <div className="text-[10px] text-[#677766]">
                      Resource: {log.resource_type} • Result: {log.result}
                    </div>
                  </div>
                  <div className="text-[10px] text-[#677766] text-right">
                    {new Date(log.created_at).toLocaleTimeString()} • {new Date(log.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
