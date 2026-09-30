import React from "react";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

interface RiskBadgeProps {
  level?: string | null;
  score?: number | null;
  showScore?: boolean;
  size?: "sm" | "md" | "lg";
}

const riskConfig: Record<string, {
  label: string;
  color: string;
  bg: string;
  border: string;
  dot: string;
}> = {
  LOW: {
    label: "Stable",
    color: "#2E7D32",
    bg: "#E8F5E9",
    border: "#A5D6A7",
    dot: "#4CAF50",
  },
  MEDIUM: {
    label: "Watch",
    color: "#F57C00",
    bg: "#FFF3E0",
    border: "#FFCC80",
    dot: "#FF9800",
  },
  HIGH: {
    label: "Attention",
    color: "#C62828",
    bg: "#FFEBEE",
    border: "#EF9A9A",
    dot: "#F44336",
  },
  MODEL_UNAVAILABLE: {
    label: "Assessment Pending",
    color: "#718096",
    bg: "#F7FAFC",
    border: "#E2E8F0",
    dot: "#A0AEC0",
  },
};

const sizeStyles: Record<"sm" | "md" | "lg", { fontSize: string; padding: string; fontWeight?: number }> = {
  sm: { fontSize: "11px", padding: "2px 8px", fontWeight: 500 },
  md: { fontSize: "12px", padding: "4px 10px", fontWeight: 500 },
  lg: { fontSize: "13px", padding: "5px 14px", fontWeight: 600 },
};

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  level = "LOW",
  score,
  showScore = false,
  size = "md",
}) => {
  const normLevel = (level || "MODEL_UNAVAILABLE").toUpperCase();
  const cfg = riskConfig[normLevel] || riskConfig.MODEL_UNAVAILABLE;
  const sz = sizeStyles[size] || sizeStyles.md;

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        borderRadius: "999px",
        border: `1px solid ${cfg.border}`,
        background: cfg.bg,
        color: cfg.color,
        fontSize: sz.fontSize,
        padding: sz.padding,
        fontWeight: sz.fontWeight || 500,
        letterSpacing: "0.02em",
      }}
    >
      <span
        style={{
          width: "7px",
          height: "7px",
          borderRadius: "50%",
          background: cfg.dot,
          flexShrink: 0,
          display: "inline-block",
        }}
      />
      <span>{cfg.label}</span>
      {showScore && score !== undefined && score !== null && (
        <span style={{ opacity: 0.8, fontWeight: 400, fontSize: "0.92em" }}>
          {Math.round(score)}/100
        </span>
      )}
    </span>
  );
};

// Circular risk gauge display (for dashboards and assessment results)
export const RiskScoreDisplay: React.FC<{ score: number; level: string; dark?: boolean }> = ({ score, level, dark = false }) => {
  const normLevel = (level || "LOW").toUpperCase();
  const cfg = riskConfig[normLevel] || riskConfig.LOW;
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const numScore = Number.isFinite(Number(score)) ? Number(score) : 0;
  const progress = Math.min(100, Math.max(0, numScore));
  const dashOffset = circumference - (progress / 100) * circumference;

  return (
    <div style={{ display: "inline-flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
      <div style={{ position: "relative", width: "120px", height: "120px" }}>
        <svg width="120" height="120" style={{ transform: "rotate(-90deg)" }}>
          <circle
            cx="60" cy="60" r={radius}
            fill="none"
            stroke={dark ? "rgba(255,255,255,0.15)" : "#E2E8F0"}
            strokeWidth="10"
          />
          <circle
            cx="60" cy="60" r={radius}
            fill="none"
            stroke={cfg.dot}
            strokeWidth="10"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>
        <div style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}>
          <span style={{ fontSize: "24px", fontWeight: 800, color: dark ? "#FFFFFF" : "#243D20" }}>
            {Math.round(progress)}
          </span>
          <span style={{ fontSize: "11px", fontWeight: 500, color: dark ? "rgba(255,255,255,0.7)" : "#718096" }}>
            out of 100
          </span>
        </div>
      </div>
      <div style={{ textAlign: "center" }}>
        <span style={{
          fontSize: "12px",
          fontWeight: 600,
          padding: "2px 8px",
          borderRadius: "999px",
          background: cfg.bg,
          color: cfg.color,
          border: `1px solid ${cfg.border}`,
        }}>
          {cfg.label}
        </span>
      </div>
    </div>
  );
};
