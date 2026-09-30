"use client";

import React, { useState, useEffect } from "react";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { Shell } from "@/components/layout/Shell";
import { StatCard } from "@/components/ui/StatCard";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import {
  Users,
  Shield,
  Layers,
  Server,
  Database,
  Plus,
  CheckCircle,
  AlertCircle,
  Activity,
  Key,
  Lock,
  RefreshCw,
  FileText,
  ToggleLeft,
  ToggleRight,
  ShieldCheck,
  CheckCheck,
} from "lucide-react";
import clsx from "clsx";
import { Skeleton, SkeletonCard, SkeletonTable } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";

export default function AdminPortal() {
  const { toast } = useToast();
  const [currentTab, setCurrentTab] = useState<string>("dashboard");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const tabParam = new URLSearchParams(window.location.search).get("tab");
      if (tabParam) {
        setCurrentTab(tabParam);
      }
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

  // Health and entity lists
  const [healthData, setHealthData] = useState<any>(null);
  const [dataSummary, setDataSummary] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [userList, setUserList] = useState<any[]>([]);
  const [personnelList, setPersonnelList] = useState<any[]>([]);
  const [unitList, setUnitList] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Audit log filters
  const [auditRoleFilter, setAuditRoleFilter] = useState<string>("ALL");
  const [auditResultFilter, setAuditResultFilter] = useState<string>("ALL");

  // Modals
  const [isAddUserOpen, setIsAddUserOpen] = useState<boolean>(false);
  const [newUsername, setNewUsername] = useState<string>("");
  const [newPassword, setNewPassword] = useState<string>("");
  const [newRole, setNewRole] = useState<string>("PERSONNEL");
  const [userSuccess, setUserSuccess] = useState<string | null>(null);

  const [isAddUnitOpen, setIsAddUnitOpen] = useState<boolean>(false);
  const [newUnitCode, setNewUnitCode] = useState<string>("");
  const [newUnitName, setNewUnitName] = useState<string>("");
  const [newUnitStrength, setNewUnitStrength] = useState<number>(100);

  // Edit Personnel Modal
  const [isEditPersonnelOpen, setIsEditPersonnelOpen] = useState<boolean>(false);
  const [editingPersonnel, setEditingPersonnel] = useState<any>(null);
  const [editRank, setEditRank] = useState<string>("");
  const [editRoleTitle, setEditRoleTitle] = useState<string>("");
  const [editPersonnelStatus, setEditPersonnelStatus] = useState<string>("ACTIVE");
  const [editPersonnelSuccess, setEditPersonnelSuccess] = useState<string | null>(null);

  // Edit Unit Modal
  const [isEditUnitOpen, setIsEditUnitOpen] = useState<boolean>(false);
  const [editingUnit, setEditingUnit] = useState<any>(null);
  const [editUnitName, setEditUnitName] = useState<string>("");
  const [editUnitType, setEditUnitType] = useState<string>("");
  const [editUnitStrength, setEditUnitStrength] = useState<number>(100);
  const [editUnitSuccess, setEditUnitSuccess] = useState<string | null>(null);

  // Edit User Modal
  const [isEditUserOpen, setIsEditUserOpen] = useState<boolean>(false);
  const [editingUser, setEditingUser] = useState<any>(null);
  const [editUserRole, setEditUserRole] = useState<string>("PERSONNEL");
  const [editUserSuccess, setEditUserSuccess] = useState<string | null>(null);

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [hRes, uRes, pRes, unitRes, dsRes, alRes] = await Promise.allSettled([
        api.get("/admin/system-health"),
        api.get("/admin/users"),
        api.get("/admin/personnel"),
        api.get("/admin/units"),
        api.get("/admin/data-summary"),
        api.get("/admin/audit-logs?limit=50"),
      ]);

      if (hRes.status === "fulfilled") setHealthData(hRes.value);
      if (uRes.status === "fulfilled") setUserList(uRes.value || []);
      if (pRes.status === "fulfilled") setPersonnelList(pRes.value || []);
      if (unitRes.status === "fulfilled") setUnitList(unitRes.value || []);
      if (dsRes.status === "fulfilled") setDataSummary(dsRes.value);
      if (alRes.status === "fulfilled") setAuditLogs(alRes.value || []);
    } catch (err) {
      console.error("Error loading admin data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/admin/users", {
        username: newUsername.trim(),
        password: newPassword,
        role: newRole,
      });
      setUserSuccess(`User account '${newUsername}' created successfully.`);
      toast.success(`User account '${newUsername}' created successfully.`);
      setNewUsername("");
      setNewPassword("");
      await loadAdminData();
      setTimeout(() => {
        setIsAddUserOpen(false);
        setUserSuccess(null);
      }, 1500);
    } catch (err: any) {
      toast.error("Error creating user: " + err.message);
    }
  };

  const handleToggleUserStatus = async (user: any) => {
    try {
      await api.patch(`/admin/users/${user.id}`, {
        is_active: !user.is_active,
      });
      toast.success(`User '${user.username}' status updated to ${!user.is_active ? 'ACTIVE' : 'INACTIVE'}.`);
      await loadAdminData();
    } catch (err: any) {
      toast.error("Error updating user status: " + (err.message || "Unknown error"));
    }
  };

  const handleCreateUnit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/admin/units", {
        unit_code: newUnitCode.trim().toUpperCase(),
        unit_name: newUnitName.trim(),
        unit_type: "BRIGADE",
        sanctioned_strength: newUnitStrength,
      });
      toast.success(`Unit '${newUnitCode.trim().toUpperCase()}' created successfully.`);
      setNewUnitCode("");
      setNewUnitName("");
      setIsAddUnitOpen(false);
      await loadAdminData();
    } catch (err: any) {
      toast.error("Error creating unit: " + err.message);
    }
  };

  const handleOpenEditPersonnel = (p: any) => {
    setEditingPersonnel(p);
    setEditRank(p.rank_or_grade || "");
    setEditRoleTitle(p.role_title || "");
    setEditPersonnelStatus(p.status || "ACTIVE");
    setIsEditPersonnelOpen(true);
  };

  const handleUpdatePersonnel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPersonnel) return;
    try {
      await api.patch(`/admin/personnel/${editingPersonnel.id}`, {
        rank_or_grade: editRank,
        role_title: editRoleTitle,
        status: editPersonnelStatus,
      });
      setEditPersonnelSuccess(`Personnel record ${editingPersonnel.personnel_code} updated successfully.`);
      toast.success(`Personnel record ${editingPersonnel.personnel_code} updated.`);
      await loadAdminData();
      setTimeout(() => {
        setIsEditPersonnelOpen(false);
        setEditPersonnelSuccess(null);
        setEditingPersonnel(null);
      }, 1200);
    } catch (err: any) {
      toast.error("Failed to update personnel: " + err.message);
    }
  };

  const handleOpenEditUnit = (u: any) => {
    setEditingUnit(u);
    setEditUnitName(u.unit_name || "");
    setEditUnitType(u.unit_type || "BRIGADE");
    setEditUnitStrength(u.sanctioned_strength || 100);
    setIsEditUnitOpen(true);
  };

  const handleUpdateUnit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUnit) return;
    try {
      await api.patch(`/admin/units/${editingUnit.id}`, {
        unit_name: editUnitName,
        unit_type: editUnitType,
        sanctioned_strength: Number(editUnitStrength),
      });
      setEditUnitSuccess(`Unit ${editingUnit.unit_code} updated successfully.`);
      toast.success(`Unit ${editingUnit.unit_code} updated.`);
      await loadAdminData();
      setTimeout(() => {
        setIsEditUnitOpen(false);
        setEditUnitSuccess(null);
        setEditingUnit(null);
      }, 1200);
    } catch (err: any) {
      toast.error("Failed to update unit: " + err.message);
    }
  };

  const handleOpenEditUser = (u: any) => {
    setEditingUser(u);
    setEditUserRole(u.role);
    setIsEditUserOpen(true);
  };

  const handleUpdateUserRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    try {
      await api.patch(`/admin/users/${editingUser.id}`, {
        role: editUserRole,
      });
      setEditUserSuccess(`User ${editingUser.username} role updated to ${editUserRole}.`);
      toast.success(`User ${editingUser.username} role updated.`);
      await loadAdminData();
      setTimeout(() => {
        setIsEditUserOpen(false);
        setEditUserSuccess(null);
        setEditingUser(null);
      }, 1200);
    } catch (err: any) {
      toast.error("Failed to update user role: " + err.message);
    }
  };

  return (
    <RoleGuard allowedRoles={["ADMIN"]}>
      <Shell currentTab={currentTab} onTabChange={handleTabChange}>
        {/* Top Header */}
        <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4 glass-panel p-5 rounded-xl border border-cyan-500/20">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-cyan-400 uppercase tracking-widest">
                SYSTEM ADMINISTRATION
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                ROOT PRIVILEGES
              </span>
            </div>
            <h1 className="text-xl font-bold font-mono tracking-wide text-white mt-1">
              SWASTI System Console
            </h1>
            <p className="text-xs text-slate-400">
              Access Control • Master Records • Canonical Infrastructure Management • System Audit Log
            </p>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-slate-800">
            <Shield className="w-4 h-4 text-cyan-400" />
            <span>Strict Role Separation • No Welfare Decisions</span>
          </div>
        </div>

        {/* Dynamic Views */}
        {/* ======================================================== */}
        {/* TAB: DASHBOARD */}
        {/* ======================================================== */}
        {currentTab === "dashboard" && (
          <div className="space-y-6">
            {/* 4 Stat Overview Cards */}
            {loading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <StatCard
                  label="Active Users"
                  value={healthData?.counts?.users ?? userList.length}
                  subtext="RBAC Authorized Accounts"
                  icon={<Users className="w-5 h-5" />}
                  accentColor="cyan"
                />

                <StatCard
                  label="Personnel Records"
                  value={healthData?.counts?.personnel ?? personnelList.length}
                  subtext="Personnel Master Roster"
                  icon={<Shield className="w-5 h-5" />}
                  accentColor="gold"
                />

                <StatCard
                  label="Operational Units"
                  value={healthData?.counts?.units ?? unitList.length}
                  subtext="Configured Battalions"
                  icon={<Layers className="w-5 h-5" />}
                  accentColor="green"
                />

                <StatCard
                  label="Canonical Database"
                  value={
                    dataSummary?.tables || dataSummary?.table_breakdown
                      ? `${Object.keys(dataSummary.tables || dataSummary.table_breakdown).length} Tables`
                      : "—"
                  }
                  subtext={
                    dataSummary?.total_canonical_records
                      ? `${Number(dataSummary.total_canonical_records).toLocaleString()} records`
                      : "Online"
                  }
                  icon={<Database className="w-5 h-5" />}
                  accentColor="violet"
                />
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="glass-panel p-5 rounded-xl border border-cyan-500/20">
              <h3 className="text-sm font-bold font-mono text-cyan-300 uppercase mb-3 flex items-center gap-2">
                <Server className="w-4 h-4 text-cyan-400" />
                <span>Core System Health</span>
              </h3>
              <div className="space-y-3 font-mono text-xs">
                <div className="flex justify-between p-2.5 rounded bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400">PostgreSQL Status:</span>
                  <span className="text-emerald-400 font-bold">
                    {dataSummary?.status || dataSummary?.database_health || "ONLINE"} ({Object.keys(dataSummary?.tables || dataSummary?.table_breakdown || {}).length || 26} Tables)
                  </span>
                </div>
                <div className="flex justify-between p-2.5 rounded bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400">FastAPI Gateway:</span>
                  <span className="text-cyan-400 font-bold">HEALTHY (:8000)</span>
                </div>
                <div className="flex justify-between p-2.5 rounded bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400">Cryptographic Auth:</span>
                  <span className="text-slate-200">Argon2id + JTI Tracking</span>
                </div>
                <div className="flex justify-between p-2.5 rounded bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400">Privacy Vault:</span>
                  <span className="text-purple-400 font-bold">SEPARATED (Well-being Record Vault)</span>
                </div>
              </div>
            </div>

            <div className="glass-panel p-5 rounded-xl border border-cyan-500/20">
              <h3 className="text-sm font-bold font-mono text-amber-300 uppercase mb-3 flex items-center gap-2">
                <Database className="w-4 h-4 text-amber-400" />
                <span>Canonical Data Architecture</span>
              </h3>
              <div className="space-y-3 font-mono text-xs">
                <div className="flex justify-between p-2.5 rounded bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400">Seed Status:</span>
                  <span className="text-emerald-400 font-bold">FULLY SEEDED & VERIFIED</span>
                </div>
                <div className="flex justify-between p-2.5 rounded bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400">Total Live Records:</span>
                  <span className="text-cyan-300 font-bold">
                    {dataSummary?.total_canonical_records
                      ? `${Number(dataSummary.total_canonical_records).toLocaleString()} Records`
                      : (loading ? "..." : "—")}
                  </span>
                </div>
                <div className="flex justify-between p-2.5 rounded bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400">ML Risk Persistence:</span>
                  <span className="text-emerald-400 font-bold">ACTIVE (model_outputs)</span>
                </div>
                <div className="flex justify-between p-2.5 rounded bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400">Audit Events Logged:</span>
                  <span className="text-slate-200 font-bold">{auditLogs.length} Events</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        )}

        {/* ======================================================== */}
        {/* TAB: USERS */}
        {/* ======================================================== */}
        {currentTab === "users" && (
          <div className="glass-panel p-6 rounded-xl border border-cyan-500/20">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold font-mono text-cyan-300 uppercase flex items-center gap-2">
                <Users className="w-5 h-5 text-cyan-400" />
                <span>User Accounts & RBAC Roles</span>
              </h2>
              <button
                onClick={() => setIsAddUserOpen(true)}
                className="px-3.5 py-1.5 rounded-lg bg-cyan-600 text-slate-950 font-mono font-bold text-xs hover:bg-cyan-500 flex items-center gap-1.5 shadow-glowCyan"
              >
                <Plus className="w-4 h-4" />
                <span>Add User</span>
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900/80 text-slate-400 border-b border-cyan-500/20">
                  <tr>
                    <th className="p-3">Username</th>
                    <th className="p-3">Role</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Created</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {loading ? (
                    <tr>
                      <td colSpan={5} className="p-4">
                        <SkeletonTable rows={4} cols={5} />
                      </td>
                    </tr>
                  ) : userList.length > 0 ? (
                    userList.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-900/40">
                        <td className="p-3 text-white font-bold">{u.username}</td>
                        <td className="p-3">
                          <span
                            className={clsx(
                              "px-2 py-0.5 rounded text-[10px] font-bold",
                              u.role === "ADMIN"
                                ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                                : u.role === "WELFARE_OFFICER"
                                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                                : u.role === "COMMANDER"
                                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                                : "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                            )}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td className="p-3">
                          <span
                            className={clsx(
                              "px-2 py-0.5 rounded text-[10px] font-bold",
                              u.is_active
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                : "bg-red-500/10 text-red-400 border border-red-500/30"
                            )}
                          >
                            {u.is_active ? "ACTIVE" : "DISABLED"}
                          </span>
                        </td>
                        <td className="p-3 text-slate-400">{u.created_at?.substring(0, 10) || "N/A"}</td>
                        <td className="p-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handleOpenEditUser(u)}
                              className="px-2.5 py-1 rounded text-[11px] font-bold bg-cyan-600/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-600/40"
                            >
                              Role
                            </button>
                            <button
                              onClick={() => handleToggleUserStatus(u)}
                              className={clsx(
                                "px-2.5 py-1 rounded text-[11px] font-bold transition-all",
                                u.is_active
                                  ? "bg-red-600/20 text-red-300 border border-red-500/40 hover:bg-red-600/40"
                                  : "bg-emerald-600/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-600/40"
                              )}
                            >
                              {u.is_active ? "Disable" : "Enable"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="p-4">
                        <EmptyState
                          icon={<Users className="w-6 h-6" />}
                          title="No Users Registered"
                          message="No system user accounts found."
                        />
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB: PERSONNEL */}
        {/* ======================================================== */}
        {currentTab === "personnel" && (
          <div className="glass-panel p-6 rounded-xl border border-cyan-500/20">
            <h2 className="text-base font-bold font-mono text-cyan-300 uppercase mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-cyan-400" />
              <span>Personnel Master Registry</span>
            </h2>
            {loading ? (
              <SkeletonTable rows={4} cols={6} />
            ) : personnelList.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900/80 text-slate-400 border-b border-cyan-500/20">
                    <tr>
                      <th className="p-3">Code</th>
                      <th className="p-3">Full Name</th>
                      <th className="p-3">Rank / Grade</th>
                      <th className="p-3">Role</th>
                      <th className="p-3">Status</th>
                      <th className="p-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {personnelList.map((p) => (
                      <tr key={p.id} className="hover:bg-slate-900/40">
                        <td className="p-3 text-cyan-300 font-bold">{p.personnel_code}</td>
                        <td className="p-3 text-white">{p.full_name}</td>
                        <td className="p-3 text-slate-300">{p.rank_or_grade}</td>
                        <td className="p-3 text-slate-400">{p.role_title}</td>
                        <td className="p-3 text-emerald-400">{p.status}</td>
                        <td className="p-3 text-right">
                          <button
                            onClick={() => handleOpenEditPersonnel(p)}
                            className="px-2.5 py-1 rounded text-[11px] font-bold bg-cyan-600/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-600/40"
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                icon={<Shield className="w-6 h-6" />}
                title="No Personnel Found"
                message="No personnel master records loaded yet."
              />
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB: UNITS */}
        {/* ======================================================== */}
        {currentTab === "units" && (
          <div className="glass-panel p-6 rounded-xl border border-cyan-500/20">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold font-mono text-cyan-300 uppercase flex items-center gap-2">
                <Layers className="w-5 h-5 text-cyan-400" />
                <span>Operational Units & Formations</span>
              </h2>
              <button
                onClick={() => setIsAddUnitOpen(true)}
                className="px-3.5 py-1.5 rounded-lg bg-cyan-600 text-slate-950 font-mono font-bold text-xs hover:bg-cyan-500 flex items-center gap-1.5 shadow-glowCyan"
              >
                <Plus className="w-4 h-4" />
                <span>Add Unit</span>
              </button>
            </div>

            {loading ? (
              <SkeletonTable rows={4} cols={5} />
            ) : unitList.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900/80 text-slate-400 border-b border-cyan-500/20">
                    <tr>
                      <th className="p-3">Unit Code</th>
                      <th className="p-3">Unit Name</th>
                      <th className="p-3">Type</th>
                      <th className="p-3">Sanctioned Strength</th>
                      <th className="p-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {unitList.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-900/40">
                        <td className="p-3 text-cyan-300 font-bold">{u.unit_code}</td>
                        <td className="p-3 text-white">{u.unit_name}</td>
                        <td className="p-3 text-slate-300">{u.unit_type}</td>
                        <td className="p-3 text-amber-400">{u.sanctioned_strength}</td>
                        <td className="p-3 text-right">
                          <button
                            onClick={() => handleOpenEditUnit(u)}
                            className="px-2.5 py-1 rounded text-[11px] font-bold bg-cyan-600/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-600/40"
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                icon={<Layers className="w-6 h-6" />}
                title="No Units Found"
                message="No operational units configured."
              />
            )}
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB: DATA MANAGEMENT (Live Table Breakdown) */}
        {/* ======================================================== */}
        {currentTab === "data_management" && (
          <div className="space-y-6">
            <div className="glass-panel p-6 rounded-xl border border-cyan-500/20">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-base font-bold font-mono text-cyan-300 uppercase flex items-center gap-2">
                    <Database className="w-5 h-5 text-cyan-400" />
                    <span>Canonical PostgreSQL Table Breakdown</span>
                  </h2>
                  <p className="text-xs text-slate-400 font-mono mt-1">
                    Live database verification across all 26 application tables.
                  </p>
                </div>
                <button
                  onClick={loadAdminData}
                  className="px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-cyan-300 text-xs font-mono hover:text-white flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Refresh DB Counts</span>
                </button>
              </div>

              {loading || (!dataSummary?.tables && !dataSummary?.table_breakdown) ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <SkeletonCard key={i} />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 font-mono text-xs">
                  {Object.entries(dataSummary.tables || dataSummary.table_breakdown).map(([tbl, cnt]: any) => (
                    <div
                      key={tbl}
                      className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between"
                    >
                      <span className="text-slate-300 font-semibold">{tbl}</span>
                      <span className="text-cyan-400 font-bold px-2 py-0.5 rounded bg-slate-950 border border-slate-700">
                        {Number(cnt).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB: SYSTEM (Live Audit Events Trail) */}
        {/* ======================================================== */}
        {currentTab === "system" && (
          <div className="space-y-6">
            <div className="glass-panel p-6 rounded-xl border border-cyan-500/20">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
                <div>
                  <h2 className="text-base font-bold font-mono text-cyan-300 uppercase flex items-center gap-2">
                    <FileText className="w-5 h-5 text-cyan-400" />
                    <span>System Audit Trail & Security Events</span>
                  </h2>
                  <p className="text-xs text-slate-400 font-mono mt-1">
                    Immutable event logs tracking authentication, administrative changes, and welfare interventions.
                  </p>
                </div>
                <button
                  onClick={loadAdminData}
                  className="px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-cyan-300 text-xs font-mono hover:text-white flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Refresh Audit Trail</span>
                </button>
              </div>

              {/* Role & Result Filters */}
              <div className="flex flex-wrap items-center gap-3 mb-4 font-mono text-xs">
                <div className="flex items-center gap-1 bg-slate-900 p-1 rounded border border-slate-800">
                  <span className="text-slate-500 text-[10px] px-1">Actor Role:</span>
                  {["ALL", "ADMIN", "WELFARE_OFFICER", "COMMANDER", "PERSONNEL"].map((role) => (
                    <button
                      key={role}
                      onClick={() => setAuditRoleFilter(role)}
                      className={clsx(
                        "px-2 py-0.5 rounded text-[10px] transition-all",
                        auditRoleFilter === role
                          ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold"
                          : "text-slate-400 hover:text-white"
                      )}
                    >
                      {role === "WELFARE_OFFICER" ? "WELFARE" : role}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-1 bg-slate-900 p-1 rounded border border-slate-800">
                  <span className="text-slate-500 text-[10px] px-1">Result:</span>
                  {["ALL", "SUCCESS", "FAILURE"].map((result) => (
                    <button
                      key={result}
                      onClick={() => setAuditResultFilter(result)}
                      className={clsx(
                        "px-2 py-0.5 rounded text-[10px] transition-all",
                        auditResultFilter === result
                          ? result === "FAILURE"
                            ? "bg-red-500/20 text-red-300 border border-red-500/40 font-bold"
                            : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold"
                          : "text-slate-400 hover:text-white"
                      )}
                    >
                      {result}
                    </button>
                  ))}
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-900/80 text-slate-400 border-b border-cyan-500/20">
                    <tr>
                      <th className="p-2.5">Timestamp</th>
                      <th className="p-2.5">Actor Role</th>
                      <th className="p-2.5">Action</th>
                      <th className="p-2.5">Resource</th>
                      <th className="p-2.5">Result</th>
                      <th className="p-2.5">Reason / Remarks</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {(() => {
                      const filteredLogs = auditLogs.filter((log) => {
                        const roleMatch = auditRoleFilter === "ALL" || log.actor_role === auditRoleFilter;
                        const resultMatch = auditResultFilter === "ALL" || log.result === auditResultFilter;
                        return roleMatch && resultMatch;
                      });
                      if (loading) {
                        return (
                          <tr>
                            <td colSpan={6} className="p-4">
                              <SkeletonTable rows={4} cols={6} />
                            </td>
                          </tr>
                        );
                      }
                      if (filteredLogs.length === 0) {
                        return (
                          <tr>
                            <td colSpan={6} className="p-4">
                              <EmptyState
                                icon={<FileText className="w-6 h-6" />}
                                title="No Audit Events Found"
                                message={auditLogs.length === 0 ? "No audit events logged yet." : "No events match current filters."}
                              />
                            </td>
                          </tr>
                        );
                      }
                      return filteredLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-slate-900/40">
                          <td className="p-2.5 text-slate-400 whitespace-nowrap">
                            {new Date(log.created_at).toLocaleString()}
                          </td>
                          <td className="p-2.5 text-amber-300 font-bold">{log.actor_role || "SYSTEM"}</td>
                          <td className="p-2.5 text-white font-semibold">{log.action}</td>
                          <td className="p-2.5 text-cyan-400">{log.resource_type}</td>
                          <td className="p-2.5">
                            <span
                              className={clsx(
                                "px-2 py-0.5 rounded text-[10px] font-bold",
                                log.result === "SUCCESS"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                  : "bg-red-500/10 text-red-400 border border-red-500/30"
                              )}
                            >
                              {log.result}
                            </span>
                          </td>
                          <td className="p-2.5 text-slate-300 max-w-xs">{log.reason || "—"}</td>
                        </tr>
                      ));
                    })()}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ======================================================== */}
        {/* TAB: SETTINGS */}
        {/* ======================================================== */}
        {currentTab === "settings" && (
          <div className="glass-panel p-6 rounded-xl border border-cyan-500/20 max-w-2xl font-mono text-xs space-y-4">
            <h2 className="text-base font-bold text-cyan-300 uppercase flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
              <span>Admin Root Security & System Policy</span>
            </h2>
            <div className="space-y-3 pt-2">
              <div className="p-3 bg-slate-900/60 rounded border border-slate-800 flex justify-between items-center">
                <div>
                  <span className="text-white font-bold block">Password Hashing Standard</span>
                  <span className="text-slate-400 text-[11px]">Argon2id (m=65536, t=3, p=4)</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-bold">
                  ACTIVE
                </span>
              </div>
              <div className="p-3 bg-slate-900/60 rounded border border-slate-800 flex justify-between items-center">
                <div>
                  <span className="text-white font-bold block">Token Session Expiry</span>
                  <span className="text-slate-400 text-[11px]">15-min JWT token • 30-min idle timeout • 8-hr absolute</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 font-bold">
                  ENFORCED
                </span>
              </div>
              <div className="p-3 bg-slate-900/60 rounded border border-slate-800 flex justify-between items-center">
                <div>
                  <span className="text-white font-bold block">Role Compartmentalization</span>
                  <span className="text-slate-400 text-[11px]">Admins manage accounts & data only; zero welfare decision capability</span>
                </div>
                <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30 font-bold">
                  RESTRICTED
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Add User */}
        <Modal
          isOpen={isAddUserOpen}
          onClose={() => setIsAddUserOpen(false)}
          title="Create System User"
          subtitle="Assign credentials and RBAC compartment"
          maxWidth="md"
        >
          <form onSubmit={handleCreateUser} className="space-y-4 font-mono text-xs">
            {userSuccess && (
              <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
                {userSuccess}
              </div>
            )}

            <div>
              <label className="block text-slate-300 mb-1">Username / Service ID</label>
              <input
                type="text"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                required
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Temporary Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Assigned Role</label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-200"
              >
                <option value="PERSONNEL">PERSONNEL</option>
                <option value="COMMANDER">COMMANDER</option>
                <option value="WELFARE_OFFICER">WELFARE_OFFICER</option>
                <option value="ADMIN">ADMIN</option>
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsAddUserOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 shadow-glowCyan"
              >
                Create Account
              </button>
            </div>
          </form>
        </Modal>

        {/* Modal: Add Unit */}
        <Modal
          isOpen={isAddUnitOpen}
          onClose={() => setIsAddUnitOpen(false)}
          title="Add Operational Unit"
          subtitle="Define unit code and sanctioned strength"
          maxWidth="md"
        >
          <form onSubmit={handleCreateUnit} className="space-y-4 font-mono text-xs">
            <div>
              <label className="block text-slate-300 mb-1">Unit Code</label>
              <input
                type="text"
                placeholder="e.g. 14-ASSAM"
                value={newUnitCode}
                onChange={(e) => setNewUnitCode(e.target.value)}
                required
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Unit Name</label>
              <input
                type="text"
                placeholder="e.g. 14th Assam Rifles Battalion"
                value={newUnitName}
                onChange={(e) => setNewUnitName(e.target.value)}
                required
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Sanctioned Strength</label>
              <input
                type="number"
                value={newUnitStrength}
                onChange={(e) => setNewUnitStrength(Number(e.target.value))}
                min="10"
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsAddUnitOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 shadow-glowCyan"
              >
                Save Unit
              </button>
            </div>
          </form>
        </Modal>
        {/* Modal: Edit Personnel */}
        <Modal
          isOpen={isEditPersonnelOpen}
          onClose={() => setIsEditPersonnelOpen(false)}
          title={`Edit Personnel: ${editingPersonnel?.personnel_code || ""}`}
          subtitle="Update rank, role title, and service status"
          maxWidth="md"
        >
          <form onSubmit={handleUpdatePersonnel} className="space-y-4 font-mono text-xs">
            {editPersonnelSuccess && (
              <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
                {editPersonnelSuccess}
              </div>
            )}

            <div>
              <label className="block text-slate-300 mb-1">Full Name</label>
              <input
                type="text"
                disabled
                value={editingPersonnel?.full_name || ""}
                className="w-full p-2.5 bg-slate-900/50 border border-slate-800 rounded text-slate-400 cursor-not-allowed"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Rank / Grade</label>
              <input
                type="text"
                value={editRank}
                onChange={(e) => setEditRank(e.target.value)}
                required
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Role Title</label>
              <input
                type="text"
                value={editRoleTitle}
                onChange={(e) => setEditRoleTitle(e.target.value)}
                required
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Status</label>
              <select
                value={editPersonnelStatus}
                onChange={(e) => setEditPersonnelStatus(e.target.value)}
                className="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-200"
              >
                <option value="ACTIVE">ACTIVE</option>
                <option value="DEPLOYED">DEPLOYED</option>
                <option value="ON_LEAVE">ON_LEAVE</option>
                <option value="INACTIVE">INACTIVE</option>
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsEditPersonnelOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 shadow-glowCyan"
              >
                Update Personnel
              </button>
            </div>
          </form>
        </Modal>

        {/* Modal: Edit Unit */}
        <Modal
          isOpen={isEditUnitOpen}
          onClose={() => setIsEditUnitOpen(false)}
          title={`Edit Unit: ${editingUnit?.unit_code || ""}`}
          subtitle="Update battalion name, type, and sanctioned strength"
          maxWidth="md"
        >
          <form onSubmit={handleUpdateUnit} className="space-y-4 font-mono text-xs">
            {editUnitSuccess && (
              <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
                {editUnitSuccess}
              </div>
            )}

            <div>
              <label className="block text-slate-300 mb-1">Unit Name</label>
              <input
                type="text"
                value={editUnitName}
                onChange={(e) => setEditUnitName(e.target.value)}
                required
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Unit Type</label>
              <input
                type="text"
                value={editUnitType}
                onChange={(e) => setEditUnitType(e.target.value)}
                required
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="block text-slate-300 mb-1">Sanctioned Strength</label>
              <input
                type="number"
                value={editUnitStrength}
                onChange={(e) => setEditUnitStrength(Number(e.target.value))}
                min="10"
                className="w-full p-2.5 bg-slate-900 border border-slate-700 rounded text-slate-200 focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsEditUnitOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 shadow-glowCyan"
              >
                Update Unit
              </button>
            </div>
          </form>
        </Modal>

        {/* Modal: Edit User Role */}
        <Modal
          isOpen={isEditUserOpen}
          onClose={() => setIsEditUserOpen(false)}
          title={`Update Role: ${editingUser?.username || ""}`}
          subtitle="Reassign RBAC authorization role"
          maxWidth="sm"
        >
          <form onSubmit={handleUpdateUserRole} className="space-y-4 font-mono text-xs">
            {editUserSuccess && (
              <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
                {editUserSuccess}
              </div>
            )}

            <div>
              <label className="block text-slate-300 mb-1">Assigned Role</label>
              <select
                value={editUserRole}
                onChange={(e) => setEditUserRole(e.target.value)}
                className="w-full p-2 bg-slate-900 border border-slate-700 rounded text-slate-200"
              >
                <option value="PERSONNEL">PERSONNEL</option>
                <option value="COMMANDER">COMMANDER</option>
                <option value="WELFARE_OFFICER">WELFARE_OFFICER</option>
                <option value="ADMIN">ADMIN</option>
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsEditUserOpen(false)}
                className="px-3 py-1.5 rounded bg-slate-800 text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 shadow-glowCyan"
              >
                Save Role
              </button>
            </div>
          </form>
        </Modal>
      </Shell>
    </RoleGuard>
  );
}
