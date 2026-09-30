"use client";

import React, { useState, useEffect } from "react";
import { RoleGuard } from "@/components/auth/RoleGuard";
import { Shell } from "@/components/layout/Shell";
import { StatCard } from "@/components/ui/StatCard";
import { RiskBadge, RiskScoreDisplay } from "@/components/ui/RiskBadge";
import { Modal } from "@/components/ui/Modal";
import { WorkloadTrendChart } from "@/components/charts/WorkloadTrendChart";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { useAuth } from "@/lib/auth-context";
import {
  Calendar,
  Clock,
  HeartPulse,
  AlertTriangle,
  MapPin,
  LifeBuoy,
  Lock,
  CheckCircle,
  FileText,
  User,
  Send,
  Plus,
  ChevronRight,
  Shield,
  Bell,
  Activity,
  Check,
  Sparkles,
} from "lucide-react";
import { SkeletonCard, SkeletonTable } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";


type InstrumentKey = "WSI-Brief-v2" | "PSS-10" | "PHQ-9";

interface InstrumentQuestion {
  key: string;
  label: string;
  sublabel?: string;
  min?: number;
  max?: number;
  lowLabel?: string;
  highLabel?: string;
  color?: string;
  isReversed?: boolean;
}

const INSTRUMENT_DEFINITIONS: Record<
  InstrumentKey,
  {
    code: InstrumentKey;
    title: string;
    subtitle: string;
    periodicity: string;
    periodicityTag: string;
    frequencyDays: number;
    recommendedTime: string;
    description: string;
    scaleType: "slider" | "options_4" | "options_5";
    options?: { value: number; label: string; desc?: string }[];
    questions: InstrumentQuestion[];
    defaultAnswers: Record<string, number>;
  }
> = {
  "WSI-Brief-v2": {
    code: "WSI-Brief-v2",
    title: "WSI Operational Pulse",
    subtitle: "Weekly Operational Stress & Recovery Pulse",
    periodicity: "Weekly Pulse",
    periodicityTag: "Every 7 Days",
    frequencyDays: 7,
    recommendedTime: "1–2 mins",
    description: "Brief operational check-in tracking daily fatigue, operational pressure, and sleep quality.",
    scaleType: "slider",
    questions: [
      { key: "stress_level", label: "Operational Stress Level", lowLabel: "Low Stress (1)", highLabel: "High Stress (5)", min: 1, max: 5, color: "#1E88E5" },
      { key: "energy_level", label: "Energy & Vitality Reserve", lowLabel: "Exhausted (1)", highLabel: "Fully Charged (5)", min: 1, max: 5, color: "#10B981" },
      { key: "sleep_quality", label: "Sleep Restfulness (Recent Nights)", lowLabel: "Very Poor (1)", highLabel: "Restorative (5)", min: 1, max: 5, color: "#F59E0B" },
      { key: "workload_stress", label: "Workload & Schedule Pressure", lowLabel: "Manageable (1)", highLabel: "Intense (5)", min: 1, max: 5, color: "#F97316" },
      { key: "recovery_satisfaction", label: "Downtime Decompression", lowLabel: "Unsatisfied (1)", highLabel: "Satisfied (5)", min: 1, max: 5, color: "#10B981" },
    ],
    defaultAnswers: {
      stress_level: 2,
      energy_level: 4,
      sleep_quality: 3,
      workload_stress: 3,
      recovery_satisfaction: 4,
    }
  },
  "PSS-10": {
    code: "PSS-10",
    title: "PSS-10 Perceived Stress Scale",
    subtitle: "Monthly Coping & Stress Overload Inventory",
    periodicity: "Monthly Inventory",
    periodicityTag: "Every 30 Days",
    frequencyDays: 30,
    recommendedTime: "3–4 mins",
    description: "Validated 10-item Cohen scale measuring feelings of unpredictability, lack of control, and stress overload over the past month.",
    scaleType: "options_5",
    options: [
      { value: 0, label: "Never", desc: "0" },
      { value: 1, label: "Almost Never", desc: "1" },
      { value: 2, label: "Sometimes", desc: "2" },
      { value: 3, label: "Fairly Often", desc: "3" },
      { value: 4, label: "Very Often", desc: "4" },
    ],
    questions: [
      { key: "pss_1", label: "1. Been upset because of something that happened unexpectedly?" },
      { key: "pss_2", label: "2. Felt unable to control the important things in your life?" },
      { key: "pss_3", label: "3. Felt nervous and stressed?" },
      { key: "pss_4", label: "4. Felt confident about your ability to handle personal problems?", isReversed: true },
      { key: "pss_5", label: "5. Felt that things were going your way?", isReversed: true },
      { key: "pss_6", label: "6. Found that you could not cope with all the things you had to do?" },
      { key: "pss_7", label: "7. Been able to control irritations in your daily life?", isReversed: true },
      { key: "pss_8", label: "8. Felt that you were on top of things?", isReversed: true },
      { key: "pss_9", label: "9. Been angered because of things outside of your control?" },
      { key: "pss_10", label: "10. Felt difficulties were piling up so high that you could not overcome them?" },
    ],
    defaultAnswers: {
      pss_1: 1, pss_2: 1, pss_3: 1, pss_4: 3, pss_5: 3,
      pss_6: 1, pss_7: 3, pss_8: 3, pss_9: 1, pss_10: 1
    }
  },
  "PHQ-9": {
    code: "PHQ-9",
    title: "PHQ-9 Wellness Screen",
    subtitle: "Fortnightly Mood, Vitality & Health Screen",
    periodicity: "Fortnightly Screen",
    periodicityTag: "Every 14–30 Days",
    frequencyDays: 14,
    recommendedTime: "2–3 mins",
    description: "Standardized 9-question instrument assessing emotional balance, focus, and energy over the last two weeks.",
    scaleType: "options_4",
    options: [
      { value: 0, label: "Not at all", desc: "0" },
      { value: 1, label: "Several days", desc: "1" },
      { value: 2, label: "More than half", desc: "2" },
      { value: 3, label: "Nearly every day", desc: "3" },
    ],
    questions: [
      { key: "phq_1", label: "1. Little interest or pleasure in doing things" },
      { key: "phq_2", label: "2. Feeling down, depressed, or hopeless" },
      { key: "phq_3", label: "3. Trouble falling or staying asleep, or sleeping too much" },
      { key: "phq_4", label: "4. Feeling tired or having little energy" },
      { key: "phq_5", label: "5. Poor appetite or overeating" },
      { key: "phq_6", label: "6. Feeling bad about yourself — or that you are a failure" },
      { key: "phq_7", label: "7. Trouble concentrating on tasks, reading, or duties" },
      { key: "phq_8", label: "8. Moving or speaking slowly, or being unusually fidgety" },
      { key: "phq_9", label: "9. Thoughts of self-harm or that you would be better off away" },
    ],
    defaultAnswers: {
      phq_1: 0, phq_2: 0, phq_3: 0, phq_4: 0, phq_5: 0,
      phq_6: 0, phq_7: 0, phq_8: 0, phq_9: 0
    }
  }
};

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

const SectionHeader: React.FC<SectionHeaderProps> = ({ title, subtitle, action }) => (
  <div className="flex items-start justify-between mb-5">
    <div>
      <h2 className="text-lg font-bold text-prahari-textPrimary">{title}</h2>
      {subtitle && <p className="text-sm text-prahari-textMuted mt-0.5">{subtitle}</p>}
    </div>
    {action}
  </div>
);

export default function PersonnelPortal() {
  const { toast } = useToast();
  const { user } = useAuth();
  const [currentTab, setCurrentTab] = useState<string>("dashboard");

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

  // Data states
  const [profile, setProfile] = useState<any>(null);
  const [deployments, setDeployments] = useState<any[]>([]);
  const [duties, setDuties] = useState<any[]>([]);
  const [leaves, setLeaves] = useState<any[]>([]);
  const [wellbeingResults, setWellbeingResults] = useState<any[]>([]);
  const [riskData, setRiskData] = useState<any>(null);
  const [workloadStats, setWorkloadStats] = useState<any>(null);
  const [leaveBalance, setLeaveBalance] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Well-being assessment modal & multi-instrument state
  const [isAssessmentOpen, setIsAssessmentOpen] = useState<boolean>(false);
  const [assessmentStep, setAssessmentStep] = useState<number>(1);
  const [assessmentConsent, setAssessmentConsent] = useState<boolean>(true);
  const [selectedInstrument, setSelectedInstrument] = useState<InstrumentKey>("WSI-Brief-v2");
  const [assessmentAnswers, setAssessmentAnswers] = useState<Record<string, number>>(
    INSTRUMENT_DEFINITIONS["WSI-Brief-v2"].defaultAnswers
  );
  const [isSubmittingAssessment, setIsSubmittingAssessment] = useState<boolean>(false);
  const [assessmentComplete, setAssessmentComplete] = useState<boolean>(false);

  const getInstrumentStatus = (key: InstrumentKey) => {
    const match = wellbeingResults.find(
      (r) => r.instrument_name === key || (key === "WSI-Brief-v2" && (!r.instrument_name || r.instrument_name.includes("WSI")))
    );
    if (!match) {
      return {
        hasDone: false,
        lastDate: null,
        daysAgo: null,
        isDue: true,
        statusLabel: "Due for Check-in",
        categoryLabel: null,
      };
    }
    const lastDate = new Date(match.assessment_date);
    const now = new Date();
    const diffDays = Math.max(0, Math.floor((now.getTime() - lastDate.getTime()) / (1000 * 60 * 60 * 24)));
    const freq = INSTRUMENT_DEFINITIONS[key].frequencyDays;
    const isDue = diffDays >= freq;
    return {
      hasDone: true,
      lastDate: match.assessment_date,
      daysAgo: diffDays,
      isDue,
      statusLabel: isDue ? `Due (${diffDays}d since last)` : `Current (${diffDays}d ago)`,
      categoryLabel: match.category_label?.replace("_", " ") || "Satisfactory",
    };
  };

  const switchInstrument = (newInst: InstrumentKey) => {
    setSelectedInstrument(newInst);
    setAssessmentAnswers({ ...INSTRUMENT_DEFINITIONS[newInst].defaultAnswers });
  };

  const openAssessmentModal = (inst: InstrumentKey = "WSI-Brief-v2") => {
    setSelectedInstrument(inst);
    setAssessmentAnswers({ ...INSTRUMENT_DEFINITIONS[inst].defaultAnswers });
    setAssessmentStep(1);
    setAssessmentComplete(false);
    setIsAssessmentOpen(true);
  };

  // Privacy toggles & modal (Screen 7 from reference image)
  const [optionalBiometrics, setOptionalBiometrics] = useState<boolean>(false);
  const [voluntaryHealthRecords, setVoluntaryHealthRecords] = useState<boolean>(false);
  const [isPrivacyPolicyOpen, setIsPrivacyPolicyOpen] = useState<boolean>(false);

  // Support request modal
  const [isSupportOpen, setIsSupportOpen] = useState<boolean>(false);
  const [supportText, setSupportText] = useState<string>("");
  const [supportPriority, setSupportPriority] = useState<string>("NORMAL");
  const [isSubmittingSupport, setIsSubmittingSupport] = useState<boolean>(false);

  // Leave application modal
  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState<boolean>(false);
  const [leaveType, setLeaveType] = useState<string>("Annual Leave");
  const [leaveStartDate, setLeaveStartDate] = useState<string>("");
  const [leaveEndDate, setLeaveEndDate] = useState<string>("");
  const [leaveReason, setLeaveReason] = useState<string>("");
  const [isSubmittingLeave, setIsSubmittingLeave] = useState<boolean>(false);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [profRes, depRes, dutRes, leaveRes, wbRes, riskRes, wlRes, balRes] = await Promise.allSettled([
        api.get("/personnel/me"),
        api.get("/personnel/me/deployments"),
        api.get("/personnel/me/duties"),
        api.get("/personnel/me/leave"),
        api.get("/personnel/me/wellbeing"),
        api.get("/personnel/me/risk"),
        api.get("/personnel/me/workload-stats"),
        api.get("/personnel/me/leave-balance"),
      ]);
      if (profRes.status === "fulfilled") setProfile(profRes.value);
      if (depRes.status === "fulfilled") setDeployments(depRes.value || []);
      if (dutRes.status === "fulfilled") setDuties(dutRes.value || []);
      if (leaveRes.status === "fulfilled") setLeaves(leaveRes.value || []);
      if (wbRes.status === "fulfilled") setWellbeingResults(wbRes.value || []);
      if (riskRes.status === "fulfilled") setRiskData(riskRes.value);
      if (wlRes.status === "fulfilled") setWorkloadStats(wlRes.value);
      if (balRes.status === "fulfilled") setLeaveBalance(balRes.value);
    } catch (e) {
      console.error("Error loading personnel data", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAllData(); }, []);

  const handleAssessmentSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsSubmittingAssessment(true);
    try {
      const activeDef = INSTRUMENT_DEFINITIONS[selectedInstrument];
      await api.post("/personnel/me/wellbeing", {
        instrument_name: activeDef.code,
        instrument_version: activeDef.code === "WSI-Brief-v2" ? "2.0" : "1.0",
        consent_given: true,
        answers: assessmentAnswers,
      });
      
      const [wbRes, rkRes] = await Promise.allSettled([
        api.get("/personnel/me/wellbeing"),
        api.get("/personnel/me/risk"),
      ]);
      if (wbRes.status === "fulfilled") setWellbeingResults(wbRes.value || []);
      if (rkRes.status === "fulfilled") setRiskData(rkRes.value);

      setAssessmentComplete(true);
      toast.success(`${activeDef.title} recorded in private vault.`);
    } catch (err: any) {
      toast.error("Submission error: " + (err?.message || "Failed to record check-in"));
    } finally {
      setIsSubmittingAssessment(false);
    }
  };

  const handleSupportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supportText.trim()) return;
    setIsSubmittingSupport(true);
    try {
      await api.post("/personnel/me/support", {
        request_type: "WELFARE_ASSISTANCE",
        priority: supportPriority,
        request_text: supportText,
      });
      toast.success("Support request dispatched to Welfare Officer.");
      setSupportText("");
      setIsSupportOpen(false);
    } catch (err: any) {
      toast.error("Error: " + err.message);
    } finally {
      setIsSubmittingSupport(false);
    }
  };

  const handleLeaveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!leaveStartDate || !leaveEndDate) return;
    setIsSubmittingLeave(true);
    try {
      await api.post("/personnel/me/leave", {
        leave_type: leaveType.replace(" Leave", "").toUpperCase(),
        start_date: leaveStartDate,
        end_date: leaveEndDate,
        reason: leaveReason || "Personal/Welfare leave",
      });
      toast.success("Leave application submitted for Commander approval.");
      setIsLeaveModalOpen(false);
      setLeaveStartDate("");
      setLeaveEndDate("");
      setLeaveReason("");
      const [lRes, bRes] = await Promise.allSettled([
        api.get("/personnel/me/leave"),
        api.get("/personnel/me/leave-balance"),
      ]);
      if (lRes.status === "fulfilled") setLeaves(lRes.value || []);
      if (bRes.status === "fulfilled") setLeaveBalance(bRes.value);
    } catch (err: any) {
      toast.error("Failed to submit leave request: " + (err?.response?.data?.detail || err.message));
    } finally {
      setIsSubmittingLeave(false);
    }
  };

  const sliderQuestions = [
    { key: "stress_level", label: "Stress Level", low: "Low", high: "High", color: "#1E88E5" },
    { key: "energy_level", label: "Energy Level", low: "Low", high: "High", color: "#10B981" },
    { key: "sleep_quality", label: "Sleep Quality", low: "Poor", high: "Good", color: "#F59E0B" },
    { key: "workload_stress", label: "Workload Perception", low: "Light", high: "Heavy", color: "#F97316" },
    { key: "recovery_satisfaction", label: "Mood", low: "Negative", high: "Positive", color: "#10B981" },
  ];

  const stepperLabels = ["Mood", "Sleep", "Stress", "Lifestyle", "Submit"];

  return (
    <RoleGuard allowedRoles={["PERSONNEL"]}>
      <Shell currentTab={currentTab} onTabChange={handleTabChange}>

        {/* ─── Dashboard Tab ──────────────────── */}
        {currentTab === "dashboard" && (
          <div className="space-y-5 animate-fade-in">
            {/* Welcome Banner */}
            <div
              className="rounded-2xl p-5 text-white shadow-card"
              style={{ background: "linear-gradient(135deg, #243D20 0%, #2E4F28 50%, #385E31 100%)" }}
            >
              <p className="text-sm text-[#CDE0CB] mb-0.5">Good Morning,</p>
              <h1 className="text-xl font-bold">{profile?.full_name || user?.username || "Personnel"} 👋</h1>
              <p className="text-sm text-[#CDE0CB]/90 mt-0.5">
                {profile?.rank_or_grade || ""} · {profile?.personnel_code || ""}
              </p>

              {/* Welfare status card inside banner */}
              <div
                className="mt-4 rounded-xl p-4"
                style={{ background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.2)" }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white">Your Welfare Status</span>
                  <ChevronRight
                    className="w-4 h-4 text-white/70 cursor-pointer"
                    onClick={() => handleTabChange("risk")}
                  />
                </div>
                <div className="flex items-center gap-4">
                  <RiskScoreDisplay
                    score={riskData?.risk_score ?? 0}
                    level={riskData?.risk_level || "LOW"}
                    dark={true}
                  />
                  <div className="text-xs text-[#CDE0CB]">
                    <div>Last model run: {riskData?.prediction_date || "Today"}</div>
                    {wellbeingResults.length > 0 && (
                      <div className="text-emerald-200 font-semibold mt-1 flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-300 inline-block animate-pulse" />
                        Latest Check-in: {wellbeingResults[0].category_label?.replace("_", " ") || "Satisfactory"} ({wellbeingResults[0].assessment_date || "Today"})
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Stat Cards */}
            {loading ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[1,2,3,4].map(i => <SkeletonCard key={i} />)}
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <StatCard
                  label="Duty Hours This Week"
                  value={`${workloadStats?.weekly_duty_hours ?? workloadStats?.weekly_total_hours ?? "—"} hrs`}
                  icon={<Clock style={{ width: "18px", height: "18px" }} />}
                  accentColor="blue"
                />
                <StatCard
                  label="Deployment This Month"
                  value={`${deployments.filter(d => !d.end_date).length} Active`}
                  icon={<MapPin style={{ width: "18px", height: "18px" }} />}
                  accentColor="gold"
                />
                <StatCard
                  label="Leave Balance"
                  value={leaveBalance ? `${Math.round(leaveBalance.total_remaining ?? ((leaveBalance.annual_remaining || 0) + (leaveBalance.casual_remaining || 0)))} days` : "—"}
                  subtext={leaveBalance ? `Annual: ${Math.round(leaveBalance.annual_remaining || 0)} · Casual: ${Math.round(leaveBalance.casual_remaining || 0)}` : ""}
                  icon={<Calendar style={{ width: "18px", height: "18px" }} />}
                  accentColor="green"
                />
                <StatCard
                  label="Upcoming Training"
                  value="—"
                  icon={<Shield style={{ width: "18px", height: "18px" }} />}
                  accentColor="violet"
                />
              </div>
            )}

            {/* Take Wellness Assessment CTA */}
            <div
              className="rounded-xl p-4 flex items-center justify-between cursor-pointer hover:shadow-cardHover transition-all"
              style={{ background: "#385E31", color: "#fff" }}
              onClick={() => openAssessmentModal("WSI-Brief-v2")}
            >
              <div>
                <div className="font-semibold text-sm">Take Wellness Assessment</div>
                <div className="text-xs text-[#CDE0CB] mt-0.5">A quick 2-minute check-in</div>
              </div>
              <ChevronRight className="w-5 h-5 text-white/70" />
            </div>

            {/* Workload chart */}
            {workloadStats?.daily_trend && (
              <div className="card p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-prahari-textPrimary">Duty Hours — Last 7 Days</h3>
                  <span className="text-xs text-prahari-textMuted">
                    {workloadStats.daily_trend.length > 0
                      ? `Avg ${((workloadStats.weekly_duty_hours ?? workloadStats.weekly_total_hours ?? 0) / workloadStats.daily_trend.length).toFixed(1)}h/day`
                      : ""}
                  </span>
                </div>
                <WorkloadTrendChart
                  data={workloadStats.daily_trend.map((d: any) => ({
                    label: d.day || d.label || d.date?.substring(5) || "Day",
                    hours: d.hours,
                  }))}
                />
              </div>
            )}

            {/* Recent Updates */}
            <div className="card p-5">
              <h3 className="font-semibold text-prahari-textPrimary mb-3">Recent Updates</h3>
              {duties.length > 0 ? (
                <div className="space-y-2">
                  {duties.slice(0, 3).map((d: any) => (
                    <div
                      key={d.id}
                      className="flex items-center gap-3 p-3 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors"
                      style={{ border: "1px solid #F0F4F8" }}
                      onClick={() => handleTabChange("deployment")}
                    >
                      <div
                        className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                        style={{ background: "#EFF5EE" }}
                      >
                        <Clock className="w-4 h-4" style={{ color: "#385E31" }} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-prahari-textPrimary truncate">
                          {d.duty_type || "Duty Schedule"}
                        </div>
                        <div className="text-xs text-prahari-textMuted">
                          {d.start_time ? `${d.start_time} – ${d.end_time || ""}` : d.duty_date || ""}
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 text-prahari-textMuted shrink-0" />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-prahari-textMuted">No recent duty updates.</p>
              )}
            </div>
          </div>
        )}

        {/* ─── Profile Tab ─────────────────────── */}
        {currentTab === "profile" && (
          <div className="animate-fade-in">
            <SectionHeader title="My Profile" subtitle="Your service record information" />
            <div className="card p-6">
              {/* Avatar row */}
              <div className="flex items-center gap-4 mb-6 pb-5" style={{ borderBottom: "1px solid #E2E8F0" }}>
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center text-white text-2xl font-bold shrink-0"
                  style={{ background: "linear-gradient(135deg, #243D20 0%, #385E31 100%)" }}
                >
                  {(profile?.full_name || user?.username)?.charAt(0)?.toUpperCase() || "P"}
                </div>
                <div>
                  <div className="text-xl font-bold text-prahari-textPrimary">{profile?.full_name || "—"}</div>
                  <div className="text-sm text-prahari-textMuted mt-0.5">
                    {profile?.rank_or_grade || ""} · {profile?.role_title || ""}
                  </div>
                  <div className="mt-1">
                    <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded" style={{ background: "#EFF5EE", color: "#243D20" }}>
                      {profile?.personnel_code || "—"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Personal & Identity */}
              <div className="mb-5">
                <div className="text-xs font-bold uppercase tracking-wider text-prahari-textMuted mb-3">
                  Personal & Identification
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {[
                    { label: "Full Name", value: profile?.full_name },
                    { label: "Service Code", value: profile?.personnel_code, mono: true },
                    { label: "Gender", value: profile?.gender },
                    { label: "Date of Birth", value: profile?.date_of_birth },
                    { label: "Blood Group", value: profile?.blood_group },
                    { label: "Emergency Contact", value: profile?.emergency_contact },
                  ].filter(f => f.value).map((field) => (
                    <div key={field.label} className="rounded-lg p-3" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-prahari-textMuted mb-1">{field.label}</div>
                      <div className={`text-sm font-medium text-prahari-textPrimary ${field.mono ? "font-mono font-bold" : ""}`}>{field.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Service & Rank */}
              <div className="mb-5">
                <div className="text-xs font-bold uppercase tracking-wider text-prahari-textMuted mb-3">
                  Service & Rank Information
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {[
                    { label: "Rank / Grade", value: profile?.rank_or_grade },
                    { label: "Primary Role", value: profile?.role_title },
                    { label: "Service Category", value: profile?.service_category },
                    { label: "Joining Date", value: profile?.date_of_joining },
                    { label: "Service Years", value: profile?.service_years != null ? `${profile.service_years} years` : undefined },
                    { label: "Current Status", value: profile?.status || "Active" },
                  ].filter(f => f.value).map((field) => (
                    <div key={field.label} className="rounded-lg p-3" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-prahari-textMuted mb-1">{field.label}</div>
                      <div className="text-sm font-medium text-prahari-textPrimary">{field.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Unit & Posting */}
              <div className="mb-2">
                <div className="text-xs font-bold uppercase tracking-wider text-prahari-textMuted mb-3">
                  Unit & Operational Posting
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {[
                    { label: "Assigned Unit", value: profile?.unit_name || "Assigned Company / Unit" },
                    { label: "Unit Code", value: profile?.unit_code || "—", mono: true },
                  ].map((field) => (
                    <div key={field.label} className="rounded-lg p-3" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                      <div className="text-[11px] font-semibold uppercase tracking-wider text-prahari-textMuted mb-1">{field.label}</div>
                      <div className={`text-sm font-medium text-prahari-textPrimary ${field.mono ? "font-mono" : ""}`}>{field.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-5 pt-4 flex items-center justify-between" style={{ borderTop: "1px solid #E2E8F0" }}>
                <p className="text-xs text-prahari-textMuted">Found an error in your service record?</p>
                <button
                  onClick={() => {
                    setSupportPriority("NORMAL");
                    setSupportText(`PROFILE CORRECTION REQUEST: Personnel Code: ${profile?.personnel_code || "N/A"}. Details: `);
                    setIsSupportOpen(true);
                  }}
                  className="btn-secondary text-xs py-1.5 px-3"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Request Correction
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ─── Deployment Tab ──────────────────── */}
        {currentTab === "deployment" && (
          <div className="animate-fade-in">
            <SectionHeader title="Deployment Records" subtitle="Your active and past deployment history" />
            <div className="card overflow-hidden">
              {loading ? (
                <div className="p-5"><SkeletonTable rows={4} cols={5} /></div>
              ) : deployments.length > 0 ? (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Location</th>
                      <th>Start Date</th>
                      <th>End Date</th>
                      <th>Duration</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deployments.map((d) => (
                      <tr key={d.id}>
                        <td className="font-medium">{d.location_label || d.deployment_type || "Base Assignment"}</td>
                        <td>{d.start_date || "—"}</td>
                        <td>{d.end_date || "Ongoing"}</td>
                        <td className="text-prahari-textMuted text-xs">{d.duration_days ? `${d.duration_days}d` : "—"}</td>
                        <td>
                          <span className={d.end_date ? "status-stable" : "status-low"} style={{ fontSize: "11px", padding: "2px 8px", borderRadius: "999px", display: "inline-block" }}>
                            {d.end_date ? "Completed" : "Active"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="p-6">
                  <EmptyState icon={<MapPin className="w-5 h-5" />} title="No Deployments Logged" message="No active or past deployment records found." />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ─── Leave Tab ────────────────────────── */}
        {currentTab === "leave" && (
          <div className="animate-fade-in">
            <SectionHeader
              title="Leave & Schedule"
              subtitle="Your leave records and balance"
              action={
                <button className="btn-primary text-xs py-2 px-3" onClick={() => setIsLeaveModalOpen(true)}>
                  <Plus className="w-4 h-4" /> Apply for Leave
                </button>
              }
            />

            {/* Balance cards */}
            {leaveBalance && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                <StatCard label="Annual Leave" value={`${Math.round(leaveBalance.annual_remaining || 0)} days`} accentColor="blue" />
                <StatCard label="Casual Leave" value={`${Math.round(leaveBalance.casual_remaining || 0)} days`} accentColor="green" />
                <StatCard label="Medical Leave" value={`${Math.round(leaveBalance.medical_remaining ?? Math.max(0, 15 - (leaveBalance.medical_used || 0)))} days`} accentColor="violet" />
                <StatCard label="Total Remaining" value={`${Math.round(leaveBalance.total_remaining ?? ((leaveBalance.annual_remaining || 0) + (leaveBalance.casual_remaining || 0)))} days`} accentColor="gold" />
              </div>
            )}

            <div className="card overflow-hidden">
              {loading ? (
                <div className="p-5"><SkeletonTable rows={4} cols={5} /></div>
              ) : leaves.length > 0 ? (
                <div className="table-responsive">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Start</th>
                        <th>End</th>
                        <th>Days</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leaves.map((l) => (
                        <tr key={l.id}>
                          <td className="font-medium">{l.leave_type}</td>
                          <td className="whitespace-nowrap">{l.start_date}</td>
                          <td className="whitespace-nowrap">{l.end_date}</td>
                          <td>{l.days_count ?? l.days ?? 1}</td>
                          <td>
                            <span
                              className="text-xs font-semibold px-2.5 py-1 rounded-full inline-block whitespace-nowrap"
                              style={
                                l.status === "APPROVED"
                                  ? { background: "#E8F5E9", color: "#2E7D32", border: "1px solid #A5D6A7" }
                                  : l.status === "PENDING"
                                  ? { background: "#FFF3E0", color: "#F57C00", border: "1px solid #FFCC80" }
                                  : l.status === "REJECTED"
                                  ? { background: "#FFEBEE", color: "#C62828", border: "1px solid #EF9A9A" }
                                  : { background: "#F1F5F9", color: "#475569", border: "1px solid #CBD5E1" }
                              }
                            >
                              {l.status === "PENDING" ? "Pending Approval" : l.status || "Approved"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-6">
                  <EmptyState
                    icon={<Calendar className="w-5 h-5" />}
                    title="No Leave Records"
                    message="No leave applications found."
                    action={<button className="btn-primary text-xs py-2 px-3" onClick={() => setIsLeaveModalOpen(true)}><Plus className="w-4 h-4" /> Apply for Leave</button>}
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ─── Well-being Tab ──────────────────── */}
        {currentTab === "wellbeing" && (
          <div className="animate-fade-in space-y-5">
            <SectionHeader
              title="Voluntary Well-being Vault"
              subtitle="Confidential standardized assessments (WSI, PSS-10, PHQ-9)"
              action={
                <button
                  className="btn-primary text-xs py-2 px-3 flex items-center gap-1.5"
                  onClick={() => openAssessmentModal("WSI-Brief-v2")}
                >
                  <Plus className="w-4 h-4" /> New Check-in
                </button>
              }
            />

            {/* Privacy notice */}
            <div className="rounded-xl p-4 flex items-start gap-3" style={{ background: "#F3E5F5", border: "1px solid #CE93D8" }}>
              <Lock className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "#6A1B9A" }} />
              <div className="text-xs leading-relaxed" style={{ color: "#4A148C" }}>
                <strong>PRIVATE & CONFIDENTIAL VAULT</strong> — Raw questionnaire responses are sealed in your personal encrypted vault.
                Commanders receive only unit-level statistical aggregates; Admins have zero access.
              </div>
            </div>

            {/* 3 Standardized Instruments Grid with Periodicities */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(["WSI-Brief-v2", "PSS-10", "PHQ-9"] as InstrumentKey[]).map((key) => {
                const inst = INSTRUMENT_DEFINITIONS[key];
                const status = getInstrumentStatus(key);
                return (
                  <div
                    key={key}
                    className="card p-4 flex flex-col justify-between hover:shadow-cardHover transition-all border border-slate-200"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-prahari-blue border border-blue-200">
                          {inst.periodicity}
                        </span>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                            status.isDue
                              ? "bg-amber-100 text-amber-800 border border-amber-200"
                              : "bg-emerald-100 text-emerald-800 border border-emerald-200"
                          }`}
                        >
                          {status.statusLabel}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-prahari-textPrimary">{inst.title}</h4>
                      <p className="text-xs text-prahari-textMuted mt-1 leading-relaxed">
                        {inst.description}
                      </p>
                      <div className="text-[11px] text-prahari-textSecondary mt-2.5 flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 text-prahari-textMuted" />
                        <span>{inst.recommendedTime} · {inst.questions.length} questions</span>
                      </div>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                      {status.categoryLabel ? (
                        <span className="text-[11px] text-slate-500 font-medium">
                          Last: <strong className="text-slate-700">{status.categoryLabel}</strong>
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-400">No prior submission</span>
                      )}
                      <button
                        type="button"
                        onClick={() => openAssessmentModal(key)}
                        className={`text-xs py-1.5 px-3 rounded-lg font-bold transition-all flex items-center gap-1 ${
                          status.isDue
                            ? "bg-prahari-blue text-white shadow hover:opacity-90"
                            : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                        }`}
                      >
                        <HeartPulse className="w-3.5 h-3.5" />
                        {status.isDue ? "Start Check-in" : "Retake"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Assessment History */}
            <div className="card overflow-hidden">
              {loading ? (
                <div className="p-5"><SkeletonTable rows={3} cols={3} /></div>
              ) : wellbeingResults.length > 0 ? (
                <>
                  <div className="p-4 flex items-center justify-between" style={{ borderBottom: "1px solid #E2E8F0" }}>
                    <div className="text-xs font-semibold uppercase tracking-wider text-prahari-textMuted">Assessment History</div>
                    <span className="text-xs text-prahari-textMuted">{wellbeingResults.length} records in vault</span>
                  </div>
                  {wellbeingResults.map((r) => (
                    <div key={r.id} className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors" style={{ borderBottom: "1px solid #F0F4F8" }}>
                      <div>
                        <div className="text-sm font-semibold text-prahari-textPrimary">{r.instrument_name || "Well-being Check-in"}</div>
                        <div className="text-xs text-prahari-textMuted mt-0.5">Recorded: {r.assessment_date}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className="text-xs font-semibold px-3 py-1 rounded-full"
                          style={{ background: "#F3E5F5", color: "#6A1B9A", border: "1px solid #CE93D8" }}
                        >
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
                </>
              ) : (
                <div className="p-6">
                  <EmptyState
                    icon={<HeartPulse className="w-5 h-5" />}
                    title="No Assessments Yet"
                    message="You haven't submitted any voluntary well-being assessments. Select an instrument above to start."
                    action={<button className="btn-primary text-xs py-2 px-3" onClick={() => openAssessmentModal("WSI-Brief-v2")}><HeartPulse className="w-4 h-4" /> Start Weekly Pulse</button>}
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* ─── Risk Status Tab ─────────────────── */}
        {currentTab === "risk" && (
          <div className="animate-fade-in space-y-5">
            <SectionHeader title="Early Welfare Risk Indicator" subtitle="Live multi-track welfare evaluation — operational signals & self-reported assessments" />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Score card */}
              <div className="card p-6 flex flex-col items-center text-center">
                <div className="text-sm font-semibold text-prahari-textMuted mb-4">Current Welfare Risk Status</div>
                <RiskScoreDisplay score={riskData?.risk_score ?? 0} level={riskData?.risk_level || "LOW"} />
                <p className="text-sm text-prahari-textMuted mt-4 max-w-sm leading-relaxed">
                  {riskData?.explanation?.summary || (
                    riskData?.risk_level === "LOW"
                      ? "Your operational duty hours, turnaround rest, and check-ins indicate a stable welfare status."
                      : riskData?.risk_level === "MEDIUM"
                      ? "Some operational indicators suggest welfare monitoring is warranted."
                      : "Elevated indicators — your Welfare Officer has been notified for supportive reach-out."
                  )}
                </p>
                <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-xs text-prahari-textMuted">
                  <span>Model: {riskData?.model_version || "online_multi_track_estimator"}</span>
                  <span>·</span>
                  <span>Date: {riskData?.prediction_date || "Today"}</span>
                  {riskData?.confidence_score !== undefined && riskData?.confidence_score !== null && (
                    <span className="ml-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                      Confidence: {riskData.confidence_score}%
                    </span>
                  )}
                  {riskData?.flagged_since && riskData?.risk_level === "HIGH" && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-50 text-red-700 border border-red-200">
                      Flagged since: {riskData.flagged_since}
                    </span>
                  )}
                </div>
              </div>

              {/* Contributing factors */}
              <div className="card p-5 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="font-semibold text-prahari-textPrimary">Live Contributing Factors</div>
                    <span className="text-[11px] text-prahari-textMuted">Dynamically Evaluated</span>
                  </div>
                  
                  {riskData?.contributing_factors && riskData.contributing_factors.length > 0 ? (
                    <div className="space-y-2">
                      {riskData.contributing_factors.map((f: any, i: number) => {
                        const factorText = typeof f === "string" ? f : (f?.factor || f?.human_label || "Operational indicator");
                        const isIncreasing = typeof f === "object" && (f?.direction === "RISK_INCREASING" || f?.weight >= 0.35);
                        return (
                          <div key={i} className="flex items-center justify-between gap-2.5 p-2 rounded-lg bg-slate-50/70 border border-slate-100 hover:bg-slate-100 transition-colors">
                            <div className="flex items-center gap-2 min-w-0">
                              <CheckCircle className="w-4 h-4 shrink-0" style={{ color: isIncreasing ? "#F57C00" : "#2E7D32" }} />
                              <span className="text-xs text-prahari-textSecondary font-medium truncate">{factorText}</span>
                            </div>
                            {typeof f === "object" && f?.direction && (
                              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${
                                isIncreasing ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
                              }`}>
                                {isIncreasing ? "Elevated" : "Optimal"}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-xs text-prahari-textMuted py-4 text-center">
                      No active risk indicators detected. Duties, rest turnaround, and assessment scores are within baseline thresholds.
                    </div>
                  )}
                </div>

                {/* Guidance note */}
                <div className="mt-4 p-3 rounded-lg flex items-start gap-2" style={{ background: "#EFF5EE", border: "1px solid #CDE0CB" }}>
                  <Bell className="w-4 h-4 shrink-0 mt-0.5" style={{ color: "#385E31" }} />
                  <p className="text-xs" style={{ color: "#243D20" }}>
                    <strong>Remember</strong> — If you ever feel the need to talk, reach out to your Welfare Officer. You are not alone.
                  </p>
                </div>
              </div>
            </div>

            {/* What Changed Since Last Week (v3.0) */}
            {riskData?.what_changed && riskData.what_changed.length > 0 && (
              <div className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="font-semibold text-sm text-prahari-textPrimary">Recent Trajectory Shift (What Changed Since Last Week)</div>
                  <span className="text-[11px] text-prahari-textMuted font-mono">7-Day Trajectory Delta</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {riskData.what_changed.map((ch: any, idx: number) => {
                    const isUp = ch.direction === "UP";
                    return (
                      <div key={idx} className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                        <div>
                          <div className="text-xs text-prahari-textMuted">{ch.factor}</div>
                          <div className="text-sm font-bold text-prahari-textPrimary mt-0.5">{ch.current_value}</div>
                        </div>
                        <span className={`text-xs font-bold px-2 py-1 rounded-lg ${
                          ch.impact === "INCREASING_RISK"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-emerald-100 text-emerald-800"
                        }`}>
                          {ch.change_text} {isUp ? "↑" : "↓"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Operational Baseline Metrics Breakdown (Live context) */}
            <div className="card p-5">
              <div className="font-semibold text-prahari-textPrimary mb-3">Live Operational Baseline Context</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-xs text-prahari-textMuted">Weekly Duty Hours</div>
                  <div className="text-base font-bold text-prahari-textPrimary mt-0.5">
                    {workloadStats?.weekly_duty_hours ?? workloadStats?.weekly_total_hours ?? "—"} hrs
                  </div>
                  <div className="text-[10px] text-prahari-textMuted mt-0.5">Standard: ≤ 48 hrs/wk</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-xs text-prahari-textMuted">Night Shift Load</div>
                  <div className="text-base font-bold text-prahari-textPrimary mt-0.5">
                    {duties.length > 0
                      ? `${Math.round((duties.filter((d: any) => d.shift_type === "NIGHT" || d.is_night_shift).length / duties.length) * 100)}%`
                      : "0%"}
                  </div>
                  <div className="text-[10px] text-prahari-textMuted mt-0.5">Circadian strain signal</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-xs text-prahari-textMuted">Available Leave Buffer</div>
                  <div className="text-base font-bold text-prahari-textPrimary mt-0.5">
                    {leaveBalance ? `${Math.round(leaveBalance.total_remaining ?? ((leaveBalance.annual_remaining || 0) + (leaveBalance.casual_remaining || 0)))} days` : "—"}
                  </div>
                  <div className="text-[10px] text-prahari-textMuted mt-0.5">Rest & recuperation buffer</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-xs text-prahari-textMuted">Latest Instrument Vault</div>
                  <div className="text-base font-bold text-prahari-textPrimary mt-0.5">
                    {wellbeingResults.length > 0 ? (wellbeingResults[0].instrument_name || "Check-in") : "None"}
                  </div>
                  <div className="text-[10px] text-prahari-textMuted mt-0.5">
                    {wellbeingResults.length > 0 ? (wellbeingResults[0].category_label?.replace("_", " ") || "Recorded") : "Pending voluntary input"}
                  </div>
                </div>
              </div>
            </div>

            {/* Wellness guidance */}
            <div className="card p-5 mt-5">
              <div className="font-semibold text-prahari-textPrimary mb-3">Personal Well-being Guidance</div>
              <div className="space-y-3">
                {[
                  { title: "Turnaround Rest", text: "Ensure at least 8 hours continuous rest following rotational night duty shifts." },
                  { title: "Leave Utilization", text: `Consider scheduling accumulated casual leave (${leaveBalance?.casual_remaining ?? 6} days available) for recovery.` },
                  { title: "Peer Connection", text: "Unit peer assistance channels and welfare counseling are accessible on request." },
                ].map((g, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                    <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0" style={{ background: "#EFF5EE", color: "#243D20" }}>{i + 1}</div>
                    <div>
                      <div className="text-sm font-semibold text-prahari-textPrimary">{g.title}</div>
                      <div className="text-xs text-prahari-textMuted mt-0.5">{g.text}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ─── Support Tab ─────────────────────── */}
        {currentTab === "support" && (
          <div className="animate-fade-in space-y-5">
            <SectionHeader title="Welfare Support" subtitle="Confidential assistance requests" />

            {/* Standard support */}
            <div className="card p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "#EFF5EE" }}>
                  <LifeBuoy className="w-5 h-5" style={{ color: "#385E31" }} />
                </div>
                <div>
                  <div className="font-semibold text-prahari-textPrimary">Request Welfare Assistance</div>
                  <div className="text-xs text-prahari-textMuted">Sent directly to your Welfare Officer</div>
                </div>
              </div>
              <p className="text-sm text-prahari-textSecondary mb-4 leading-relaxed">
                Submit a confidential support inquiry directly to your assigned Unit Welfare Officer. All communications are private.
              </p>
              <button
                className="btn-primary text-sm py-2.5 px-4"
                onClick={() => { setSupportPriority("NORMAL"); setSupportText(""); setIsSupportOpen(true); }}
              >
                <Send className="w-4 h-4" /> Compose Support Request
              </button>
            </div>

            {/* Emergency SOS */}
            <div className="rounded-xl p-5" style={{ background: "#FFEBEE", border: "1.5px solid #EF9A9A" }}>
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4" style={{ color: "#C62828" }} />
                <div className="font-semibold text-sm" style={{ color: "#C62828" }}>Priority Emergency Welfare Pathway</div>
              </div>
              <p className="text-sm mb-4 leading-relaxed" style={{ color: "#7F1D1D" }}>
                If you are experiencing severe distress or require immediate intervention, trigger a high-priority welfare dispatch to alert the on-duty Welfare Officer immediately.
              </p>
              <button
                className="btn-danger text-sm py-2.5 px-4"
                onClick={() => {
                  setSupportPriority("HIGH");
                  setSupportText("URGENT WELFARE REQUEST: Requesting immediate consultation with on-duty Welfare Officer.");
                  setIsSupportOpen(true);
                }}
              >
                <AlertTriangle className="w-4 h-4" /> Trigger Urgent Welfare Support
              </button>
            </div>
          </div>
        )}

        {/* ─── Settings / Privacy & Consent Tab (Screen 7) ──── */}
        {currentTab === "settings" && (
          <div className="animate-fade-in max-w-xl mx-auto space-y-6">
            {/* Header Icon + Title */}
            <div className="text-center pt-2 pb-4">
              <div
                className="w-16 h-16 rounded-2xl mx-auto mb-3 flex items-center justify-center shadow-sm"
                style={{ background: "#EFF5EE", border: "1px solid #CDE0CB" }}
              >
                <Shield className="w-8 h-8" style={{ color: "#385E31" }} />
              </div>
              <h2 className="text-xl font-bold text-prahari-textPrimary">Your Data, Your Rights</h2>
              <p className="text-sm text-prahari-textMuted mt-1">We respect your privacy. You control what data you share.</p>
            </div>

            {/* Privacy Toggles Card */}
            <div className="card p-5 space-y-4">
              {/* Item 1 */}
              <div className="flex items-center justify-between pb-3" style={{ borderBottom: "1px solid #F0F4F8" }}>
                <div className="flex-1 pr-4">
                  <div className="font-semibold text-sm text-prahari-textPrimary">Wellness Assessments</div>
                  <div className="text-xs text-prahari-textMuted mt-0.5">Required for core functionality & welfare trend monitoring</div>
                </div>
                <div className="w-11 h-6 rounded-full flex items-center p-0.5 cursor-not-allowed" style={{ background: "#385E31" }}>
                  <div className="w-5 h-5 rounded-full bg-white ml-auto shadow-sm" />
                </div>
              </div>

              {/* Item 2 */}
              <div className="flex items-center justify-between pb-3" style={{ borderBottom: "1px solid #F0F4F8" }}>
                <div className="flex-1 pr-4">
                  <div className="font-semibold text-sm text-prahari-textPrimary">Duty & Deployment Data</div>
                  <div className="text-xs text-prahari-textMuted mt-0.5">Used for fatigue prevention and operational welfare analysis</div>
                </div>
                <div className="w-11 h-6 rounded-full flex items-center p-0.5 cursor-not-allowed" style={{ background: "#385E31" }}>
                  <div className="w-5 h-5 rounded-full bg-white ml-auto shadow-sm" />
                </div>
              </div>

              {/* Item 3 */}
              <div className="flex items-center justify-between pb-3" style={{ borderBottom: "1px solid #F0F4F8" }}>
                <div className="flex-1 pr-4">
                  <div className="font-semibold text-sm text-prahari-textPrimary">Optional Biometric Data</div>
                  <div className="text-xs text-prahari-textMuted mt-0.5">Only with your explicit consent (wearables / sleep sensors)</div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const next = !optionalBiometrics;
                    setOptionalBiometrics(next);
                    toast.info(next ? "Biometric data sharing enabled." : "Biometric data sharing disabled.");
                  }}
                  className="w-11 h-6 rounded-full flex items-center p-0.5 transition-colors"
                  style={{ background: optionalBiometrics ? "#385E31" : "#CBD5E0" }}
                >
                  <div className={`w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${optionalBiometrics ? "ml-auto" : "mr-auto"}`} />
                </button>
              </div>

              {/* Item 4 */}
              <div className="flex items-center justify-between">
                <div className="flex-1 pr-4">
                  <div className="font-semibold text-sm text-prahari-textPrimary">Health Records (Voluntary)</div>
                  <div className="text-xs text-prahari-textMuted mt-0.5">For comprehensive medical welfare assistance</div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const next = !voluntaryHealthRecords;
                    setVoluntaryHealthRecords(next);
                    toast.info(next ? "Voluntary health records sharing enabled." : "Voluntary health records sharing disabled.");
                  }}
                  className="w-11 h-6 rounded-full flex items-center p-0.5 transition-colors"
                  style={{ background: voluntaryHealthRecords ? "#385E31" : "#CBD5E0" }}
                >
                  <div className={`w-5 h-5 rounded-full bg-white shadow-sm transition-transform ${voluntaryHealthRecords ? "ml-auto" : "mr-auto"}`} />
                </button>
              </div>
            </div>

            {/* Privacy Policy Link Button */}
            <button
              onClick={() => setIsPrivacyPolicyOpen(true)}
              className="w-full flex items-center justify-between p-4 card hover:bg-gray-50 transition-colors text-sm font-semibold text-prahari-textPrimary"
            >
              <span>View Privacy Policy</span>
              <ChevronRight className="w-4 h-4 text-prahari-textMuted" />
            </button>
          </div>
        )}

        {/* ── Privacy Policy Modal ─────────────── */}
        <Modal
          isOpen={isPrivacyPolicyOpen}
          onClose={() => setIsPrivacyPolicyOpen(false)}
          title="SWASTI Privacy Firewall"
          subtitle="Non-negotiable data boundaries under AGENTS.md directives"
          maxWidth="md"
        >
          <div className="space-y-4 text-sm text-prahari-textSecondary">
            <div className="p-3.5 rounded-xl" style={{ background: "#E8F5E9", border: "1px solid #A5D6A7" }}>
              <div className="font-semibold text-prahari-low mb-1">Zero Raw Answer Disclosure</div>
              <p className="text-xs text-prahari-low">
                Your voluntary questionnaire responses are encrypted into your private vault. Commanders and Admins never see raw individual responses.
              </p>
            </div>
            <div className="p-3.5 rounded-xl" style={{ background: "#E3F0FC", border: "1px solid #BFDBFE" }}>
              <div className="font-semibold text-prahari-blue mb-1">Commander Boundary</div>
              <p className="text-xs text-prahari-blue">
                Commanders only have access to anonymised battalion-level aggregates (N ≥ 5). Individual welfare profiles are strictly isolated.
              </p>
            </div>
            <div className="p-3.5 rounded-xl" style={{ background: "#FFF3E0", border: "1px solid #FFCC80" }}>
              <div className="font-semibold text-prahari-med mb-1">No Automated High-Stakes Decisions</div>
              <p className="text-xs text-prahari-med">
                SWASTI does not automatically reject leaves, alter postings, or make disciplinary decisions. All assessments serve solely to guide compassionate human welfare support.
              </p>
            </div>
            <button onClick={() => setIsPrivacyPolicyOpen(false)} className="btn-primary w-full justify-center py-2.5 mt-2">
              Understood
            </button>
          </div>
        </Modal>

        {/* ── Well-being Assessment Modal (Screens 3, 4, 7) ─────── */}
        <Modal
          isOpen={isAssessmentOpen}
          onClose={() => { setIsAssessmentOpen(false); setAssessmentComplete(false); setAssessmentStep(1); }}
          title={
            assessmentComplete
              ? "Assessment Complete"
              : assessmentStep === 1
              ? INSTRUMENT_DEFINITIONS[selectedInstrument].title
              : "Privacy & Consent Safeguards"
          }
          subtitle={
            assessmentComplete
              ? "Live welfare metrics updated in private vault"
              : assessmentStep === 1
              ? `${INSTRUMENT_DEFINITIONS[selectedInstrument].periodicity} · ${INSTRUMENT_DEFINITIONS[selectedInstrument].recommendedTime}`
              : "Confirm confidential data submission"
          }
          maxWidth="md"
        >
          {assessmentComplete ? (
            /* Screen 4: Completion screen */
            <div className="text-center py-4 space-y-4 animate-fade-in">
              <div className="text-5xl animate-bounce">🎉</div>
              <div>
                <h3 className="text-xl font-bold text-prahari-textPrimary">Assessment Complete</h3>
                <p className="text-xs text-prahari-textMuted mt-0.5">
                  {INSTRUMENT_DEFINITIONS[selectedInstrument].title} processed into your private vault
                </p>
              </div>

              <div className="py-2">
                <RiskScoreDisplay score={riskData?.risk_score ?? 0} level={riskData?.risk_level || "LOW"} dark={false} />
              </div>

              <p className="text-sm font-medium text-prahari-textSecondary">
                Your responses and duty metrics indicate a <span className={`font-bold ${riskData?.risk_level === "HIGH" ? "text-prahari-high" : riskData?.risk_level === "MEDIUM" ? "text-prahari-med" : "text-prahari-low"}`}>
                  {riskData?.risk_level === "HIGH" ? "elevated" : riskData?.risk_level === "MEDIUM" ? "monitored" : "stable"}
                </span> welfare status.
              </p>

              {/* Dynamic Live Contributing Factors */}
              <div className="text-left rounded-xl p-4 space-y-2" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                <div className="flex items-center justify-between mb-2">
                  <div className="font-bold text-xs uppercase tracking-wider text-prahari-textPrimary">Live Contributing Factors</div>
                  <span className="text-[10px] text-prahari-textMuted">Operational & Self-Report Signals</span>
                </div>
                {riskData?.contributing_factors && riskData.contributing_factors.length > 0 ? (
                  riskData.contributing_factors.map((f: any, i: number) => {
                    const factorLabel = typeof f === "string" ? f : (f?.factor || f?.human_label || "Operational factor");
                    const isIncreasing = typeof f === "object" && (f?.direction === "RISK_INCREASING" || f?.weight >= 0.35);
                    return (
                      <div key={i} className="flex items-center justify-between gap-2 text-xs py-1 border-b border-slate-100 last:border-0">
                        <div className="flex items-center gap-2 text-prahari-textSecondary min-w-0">
                          <CheckCircle className="w-4 h-4 shrink-0" style={{ color: isIncreasing ? "#F57C00" : "#2E7D32" }} />
                          <span className="truncate">{factorLabel}</span>
                        </div>
                        {typeof f === "object" && f?.direction && (
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${
                            isIncreasing ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"
                          }`}>
                            {isIncreasing ? "Elevated" : "Optimal"}
                          </span>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="text-xs text-prahari-textMuted py-1">No active stress indicators identified.</div>
                )}
              </div>

              {/* Dynamic explanation summary or reminder card */}
              <div className="rounded-xl p-3.5 text-left flex items-start gap-2.5" style={{ background: "#E3F0FC", border: "1px solid #BFDBFE" }}>
                <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">i</div>
                <div className="text-xs text-prahari-blue leading-relaxed">
                  {riskData?.explanation?.summary || (
                    <>
                      <span className="font-bold">Remember:</span> If you ever feel the need to talk, reach out to your Welfare Officer. You are not alone.
                    </>
                  )}
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  className="btn-primary flex-1 justify-center py-2.5"
                  onClick={() => { setIsAssessmentOpen(false); handleTabChange("risk"); }}
                >
                  View My Trends
                </button>
                <button
                  type="button"
                  className="btn-secondary flex-1 justify-center py-2.5"
                  onClick={() => { setIsAssessmentOpen(false); setAssessmentComplete(false); }}
                >
                  Back to Dashboard
                </button>
              </div>
            </div>
          ) : assessmentStep === 1 ? (
            /* Step 1: Instrument Selector + Questions */
            <div className="space-y-4 animate-fade-in">
              {/* Instrument Selection Segmented Control */}
              <div className="bg-slate-100 p-1.5 rounded-xl grid grid-cols-3 gap-1">
                {(["WSI-Brief-v2", "PSS-10", "PHQ-9"] as InstrumentKey[]).map((key) => {
                  const inst = INSTRUMENT_DEFINITIONS[key];
                  const status = getInstrumentStatus(key);
                  const isSelected = selectedInstrument === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => switchInstrument(key)}
                      className={`px-2.5 py-2 rounded-lg text-left transition-all ${
                        isSelected
                          ? "bg-white text-prahari-primary shadow-sm font-bold border border-slate-200"
                          : "text-prahari-textMuted hover:text-prahari-textPrimary"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="truncate">{key === "WSI-Brief-v2" ? "WSI Pulse" : key}</span>
                        <span className={`w-2 h-2 rounded-full ${status.isDue ? "bg-amber-400" : "bg-emerald-400"}`} />
                      </div>
                      <div className="text-[10px] text-prahari-textMuted mt-0.5 truncate">{inst.periodicity}</div>
                    </button>
                  );
                })}
              </div>

              {/* Selected Instrument Header & Periodicity info */}
              <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-100 flex items-start justify-between">
                <div>
                  <div className="text-xs font-bold text-prahari-textPrimary flex items-center gap-1.5">
                    <span>{INSTRUMENT_DEFINITIONS[selectedInstrument].title}</span>
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                      {INSTRUMENT_DEFINITIONS[selectedInstrument].periodicityTag}
                    </span>
                  </div>
                  <p className="text-[11px] text-prahari-textSecondary mt-0.5">
                    {INSTRUMENT_DEFINITIONS[selectedInstrument].description}
                  </p>
                </div>
                <div className="text-right shrink-0 ml-2">
                  <span className="text-[10px] text-prahari-textMuted block">Time</span>
                  <span className="text-xs font-semibold text-prahari-blue">
                    {INSTRUMENT_DEFINITIONS[selectedInstrument].recommendedTime}
                  </span>
                </div>
              </div>

              {/* Questions Rendered by Instrument Type */}
              <div className="max-h-[50vh] overflow-y-auto pr-1 space-y-3.5">
                {selectedInstrument === "WSI-Brief-v2" ? (
                  /* 5 WSI Sliders */
                  INSTRUMENT_DEFINITIONS["WSI-Brief-v2"].questions.map((q) => {
                    const val = assessmentAnswers[q.key] ?? 3;
                    const color = q.color || "#385E31";
                    return (
                      <div key={q.key} className="p-3 rounded-xl bg-slate-50/70 border border-slate-200">
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="font-semibold text-xs text-prahari-textPrimary">{q.label}</label>
                          <span
                            className="w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs text-white shadow-sm"
                            style={{ background: color }}
                          >
                            {val}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="1"
                          max="5"
                          step="1"
                          value={val}
                          onChange={(e) => setAssessmentAnswers({ ...assessmentAnswers, [q.key]: Number(e.target.value) })}
                          style={{ accentColor: color }}
                          className="w-full cursor-pointer"
                        />
                        <div className="flex justify-between text-[11px] text-prahari-textMuted mt-1">
                          <span>{q.lowLabel}</span>
                          <span>{q.highLabel}</span>
                        </div>
                      </div>
                    );
                  })
                ) : selectedInstrument === "PSS-10" ? (
                  /* 10 Cohen PSS Questions */
                  INSTRUMENT_DEFINITIONS["PSS-10"].questions.map((q) => {
                    const currentVal = assessmentAnswers[q.key] ?? 1;
                    return (
                      <div key={q.key} className="p-3 rounded-xl bg-slate-50/70 border border-slate-200">
                        <div className="text-xs font-semibold text-prahari-textPrimary mb-2 leading-relaxed">
                          {q.label}
                          {q.isReversed && (
                            <span className="text-[10px] font-normal text-emerald-600 ml-1.5">(Positive Coping)</span>
                          )}
                        </div>
                        <div className="grid grid-cols-5 gap-1.5">
                          {INSTRUMENT_DEFINITIONS["PSS-10"].options?.map((opt) => {
                            const isSelected = currentVal === opt.value;
                            return (
                              <button
                                key={opt.value}
                                type="button"
                                onClick={() => setAssessmentAnswers({ ...assessmentAnswers, [q.key]: opt.value })}
                                className={`py-2 px-1 text-center rounded-lg text-[11px] transition-all ${
                                  isSelected
                                    ? "bg-prahari-blue text-white font-bold shadow-sm"
                                    : "bg-white text-slate-700 hover:bg-slate-100 border border-slate-200"
                                }`}
                              >
                                <div className="font-bold">{opt.value}</div>
                                <div className="text-[9px] truncate">{opt.label}</div>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  /* 9 PHQ Questions */
                  INSTRUMENT_DEFINITIONS["PHQ-9"].questions.map((q) => {
                    const currentVal = assessmentAnswers[q.key] ?? 0;
                    const isSafety = q.key === "phq_9";
                    return (
                      <div key={q.key} className={`p-3 rounded-xl border ${isSafety ? "bg-amber-50/70 border-amber-300" : "bg-slate-50/70 border-slate-200"}`}>
                        <div className="text-xs font-semibold text-prahari-textPrimary mb-2 leading-relaxed">
                          {q.label}
                          {isSafety && (
                            <span className="text-[10px] font-bold text-amber-700 ml-1.5">(Priority Safety Item)</span>
                          )}
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                          {INSTRUMENT_DEFINITIONS["PHQ-9"].options?.map((opt) => {
                            const isSelected = currentVal === opt.value;
                            return (
                              <button
                                key={opt.value}
                                type="button"
                                onClick={() => setAssessmentAnswers({ ...assessmentAnswers, [q.key]: opt.value })}
                                className={`py-2 px-2 text-center rounded-lg text-[11px] transition-all ${
                                  isSelected
                                    ? "bg-prahari-blue text-white font-bold shadow-sm"
                                    : "bg-white text-slate-700 hover:bg-slate-100 border border-slate-200"
                                }`}
                              >
                                <div className="font-bold">{opt.value}</div>
                                <div className="text-[10px] leading-tight">{opt.label}</div>
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Confidential Vault Notice */}
              <div className="rounded-xl p-3 bg-blue-50/80 border border-blue-200/80 flex items-start gap-2.5">
                <Lock className="w-4 h-4 text-prahari-blue shrink-0 mt-0.5" />
                <div className="text-xs text-prahari-textSecondary">
                  <span className="font-semibold text-prahari-textPrimary">Confidential Vault: </span>
                  Voluntary check-in. Answers are encrypted directly into your private vault. Commanders and Admins cannot see raw responses.
                </div>
              </div>

              {/* Direct Submit & Action Bar (Sticky at bottom for mobile) */}
              <div className="sticky bottom-0 bg-white/95 backdrop-blur-sm pt-3 pb-1 border-t border-slate-100 flex items-center gap-3 z-10">
                <button
                  type="button"
                  className="btn-secondary flex-1 justify-center py-2.5 text-xs"
                  onClick={() => setIsAssessmentOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={isSubmittingAssessment}
                  className="btn-primary flex-2 justify-center py-2.5 text-xs font-bold shadow-md hover:shadow-lg transition-all"
                  style={{ background: "#385E31" }}
                  onClick={() => handleAssessmentSubmit()}
                >
                  {isSubmittingAssessment ? (
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 animate-spin" /> Recording...
                    </span>
                  ) : (
                    <span className="flex items-center gap-1.5">
                      <HeartPulse className="w-4 h-4 text-emerald-400" /> Submit {INSTRUMENT_DEFINITIONS[selectedInstrument].title.split(" ")[0]}
                    </span>
                  )}
                </button>
              </div>

              <div className="text-center pt-1">
                <button
                  type="button"
                  onClick={() => setAssessmentStep(2)}
                  className="text-[11px] text-prahari-olive hover:underline font-semibold"
                >
                  Review Detailed Privacy & Legal Safeguards &rarr;
                </button>
              </div>
            </div>
          ) : (
            /* Step 2: Privacy Consent before submission */
            <form onSubmit={handleAssessmentSubmit} className="space-y-5 animate-fade-in">
              <div className="rounded-xl p-4" style={{ background: "#F7FAFC", border: "1px solid #E2E8F0" }}>
                <div className="font-semibold text-sm text-prahari-textPrimary mb-1">Privacy Guarantee</div>
                <p className="text-xs text-prahari-textMuted mb-3">
                  Your individual responses are strictly confidential. Commanders only receive anonymous battalion statistics.
                </p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-xs text-prahari-textSecondary">
                    <CheckCircle className="w-4 h-4 shrink-0 text-prahari-low" />
                    <span>Responses encrypted directly to personal vault</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-prahari-textSecondary">
                    <CheckCircle className="w-4 h-4 shrink-0 text-prahari-low" />
                    <span>No automated career or disciplinary decisions</span>
                  </div>
                </div>
              </div>

              <label className="flex items-start gap-3 cursor-pointer p-3 rounded-xl border border-[#CDE0CB] bg-[#EFF5EE]/60">
                <input
                  type="checkbox"
                  required
                  checked={assessmentConsent}
                  onChange={(e) => setAssessmentConsent(e.target.checked)}
                  className="mt-0.5 w-4 h-4 rounded text-prahari-olive focus:ring-prahari-olive"
                />
                <span className="text-xs text-prahari-textPrimary leading-relaxed">
                  I voluntarily submit this wellness check-in ({INSTRUMENT_DEFINITIONS[selectedInstrument].title}) and consent to welfare pattern analysis.
                </span>
              </label>

              <div className="sticky bottom-0 bg-white/95 backdrop-blur-sm pt-3 pb-1 border-t border-slate-100 flex gap-3 z-10">
                <button
                  type="button"
                  className="btn-secondary flex-1 justify-center py-2.5 text-xs"
                  onClick={() => setAssessmentStep(1)}
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={!assessmentConsent || isSubmittingAssessment}
                  className="btn-primary flex-2 justify-center py-2.5 text-xs font-bold disabled:opacity-50"
                  style={{ background: "#385E31" }}
                >
                  {isSubmittingAssessment ? "Encrypting & Submitting..." : "Submit Assessment"}
                </button>
              </div>
            </form>
          )}
        </Modal>

        {/* ── Support Request Modal ──────────── */}
        <Modal
          isOpen={isSupportOpen}
          onClose={() => setIsSupportOpen(false)}
          title="Support Request"
          subtitle="Sent confidentially to your Welfare Officer"
          maxWidth="md"
        >
          <form onSubmit={handleSupportSubmit} className="space-y-4">
            <div>
              <label className="form-label">Priority Level</label>
              <select
                value={supportPriority}
                onChange={(e) => setSupportPriority(e.target.value)}
                className="form-input"
              >
                <option value="LOW">Routine inquiry</option>
                <option value="NORMAL">Standard support</option>
                <option value="HIGH">High priority</option>
              </select>
            </div>
            <div>
              <label className="form-label">Describe your request</label>
              <textarea
                rows={4}
                value={supportText}
                onChange={(e) => setSupportText(e.target.value)}
                placeholder="Details of assistance required (rest adjustment, welfare query, counseling)..."
                required
                className="form-input resize-none"
              />
            </div>
            <div className="flex gap-3 pt-1">
              <button type="button" className="btn-secondary flex-1 justify-center" onClick={() => setIsSupportOpen(false)}>Cancel</button>
              <button type="submit" disabled={isSubmittingSupport || !supportText.trim()} className="btn-primary flex-1 justify-center disabled:opacity-50">
                {isSubmittingSupport ? "Sending..." : "Dispatch Request"}
              </button>
            </div>
          </form>
        </Modal>

        {/* ── Leave Application Modal ────────── */}
        <Modal
          isOpen={isLeaveModalOpen}
          onClose={() => setIsLeaveModalOpen(false)}
          title="Apply for Leave"
          subtitle="Submit formal leave request for approval"
          maxWidth="md"
        >
          <form onSubmit={handleLeaveSubmit} className="space-y-4">
            <div>
              <label className="form-label">Leave Category</label>
              <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)} className="form-input">
                <option value="Annual Leave">Annual Leave</option>
                <option value="Casual Leave">Casual Leave</option>
                <option value="Medical Leave">Medical Leave</option>
                <option value="Compassionate Leave">Compassionate Leave</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="form-label">Start Date</label>
                <input type="date" required value={leaveStartDate} onChange={(e) => setLeaveStartDate(e.target.value)} className="form-input" />
              </div>
              <div>
                <label className="form-label">End Date</label>
                <input type="date" required value={leaveEndDate} onChange={(e) => setLeaveEndDate(e.target.value)} className="form-input" />
              </div>
            </div>
            <div>
              <label className="form-label">Purpose / Reason</label>
              <textarea rows={3} value={leaveReason} onChange={(e) => setLeaveReason(e.target.value)} placeholder="Reason for leave..." className="form-input resize-none" />
            </div>
            <div className="flex gap-3 pt-1">
              <button type="button" className="btn-secondary flex-1 justify-center" onClick={() => setIsLeaveModalOpen(false)}>Cancel</button>
              <button type="submit" disabled={isSubmittingLeave} className="btn-primary flex-1 justify-center disabled:opacity-50">
                {isSubmittingLeave ? "Submitting..." : "Submit Application"}
              </button>
            </div>
          </form>
        </Modal>

      </Shell>
    </RoleGuard>
  );
}
