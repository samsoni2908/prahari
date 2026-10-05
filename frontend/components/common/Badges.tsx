"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, AlertCircle, HelpCircle, Clock, ShieldCheck } from "lucide-react";

export type RiskTier = "LOW" | "MEDIUM" | "HIGH" | "MODEL_UNAVAILABLE" | string;

export interface RiskBadgeProps {
  level?: RiskTier | null;
  score?: number | null;
  showScore?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  level = "LOW",
  score,
  showScore = false,
  size = "md",
  className = "",
}) => {
  const norm = (level || "MODEL_UNAVAILABLE").toUpperCase();

  const configs: Record<string, { label: string; bg: string; text: string; border: string; dot: string }> = {
    LOW: {
      label: "Stable",
      bg: "bg-[#ECFDF5]",
      text: "text-[#15803D]",
      border: "border-[#A7F3D0]",
      dot: "bg-[#22C55E]",
    },
    MEDIUM: {
      label: "Watch",
      bg: "bg-[#FFFBEB]",
      text: "text-[#B45309]",
      border: "border-[#FDE68A]",
      dot: "bg-[#F59E0B]",
    },
    HIGH: {
      label: "Attention",
      bg: "bg-[#FEF2F2]",
      text: "text-[#B91C1C]",
      border: "border-[#FECACA]",
      dot: "bg-[#EF4444]",
    },
    MODEL_UNAVAILABLE: {
      label: "Pending / Stale",
      bg: "bg-[#F3F4F6]",
      text: "text-[#4B5563]",
      border: "border-[#E5E7EB]",
      dot: "bg-[#9CA3AF]",
    },
  };

  const cfg = configs[norm] || configs.MODEL_UNAVAILABLE;

  const sizeClass = {
    sm: "text-[10px] px-2 py-0.5 gap-1",
    md: "text-xs px-2.5 py-1 gap-1.5 font-medium",
    lg: "text-sm px-3.5 py-1.5 gap-2 font-semibold",
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-full border ${cfg.bg} ${cfg.text} ${cfg.border} ${sizeClass} tracking-wide select-none ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} shrink-0 animate-pulse`} />
      <span>{cfg.label}</span>
      {showScore && score !== undefined && score !== null && (
        <span className="opacity-75 font-mono text-[0.9em]">
          ({Math.round(score)})
        </span>
      )}
    </span>
  );
};

export interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = "md",
  className = "",
}) => {
  const norm = (status || "UNKNOWN").toUpperCase();

  const getStyle = () => {
    switch (norm) {
      case "ACTIVE":
      case "ON_DUTY":
      case "RESOLVED":
      case "COMPLETED":
        return "bg-[#ECFDF5] text-[#15803D] border-[#A7F3D0]";
      case "PENDING":
      case "MONITOR":
      case "FOLLOWUP":
      case "STANDBY":
        return "bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]";
      case "CRITICAL":
      case "OVERDUE":
      case "URGENT":
        return "bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]";
      case "ON_LEAVE":
        return "bg-[#EFF6FF] text-[#1D4ED8] border-[#BFDBFE]";
      default:
        return "bg-[#F3F4F6] text-[#4B5563] border-[#E5E7EB]";
    }
  };

  const sizeClass = size === "sm" ? "text-[10px] px-2 py-0.5" : "text-xs px-2.5 py-0.5 font-medium";

  return (
    <span
      className={`inline-flex items-center rounded-md border font-mono tracking-wider ${getStyle()} ${sizeClass} select-none ${className}`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
};

export type TruthState =
  | "AVAILABLE"
  | "UNAVAILABLE"
  | "NOT_COMPUTED"
  | "DATA_STALE"
  | "INSUFFICIENT_DATA"
  | "SUPPRESSED"
  | "NOT_ACTIVATED";

export const AvailabilityBadge: React.FC<{ state: TruthState; label?: string }> = ({
  state,
  label,
}) => {
  const isAvailable = state === "AVAILABLE";

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono border ${
        isAvailable
          ? "bg-[#ECFDF5] text-[#15803D] border-[#A7F3D0]"
          : "bg-[#F3F4F6] text-[#4B5563] border-[#E5E7EB]"
      }`}
    >
      {isAvailable ? (
        <CheckCircle2 className="h-3 w-3 text-[#15803D]" />
      ) : (
        <HelpCircle className="h-3 w-3 text-[#6B7280]" />
      )}
      <span>{label || state.replace(/_/g, " ")}</span>
    </span>
  );
};
