import React from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  accentColor?: "cyan" | "gold" | "green" | "amber" | "red" | "violet" | "blue" | "olive";
  trend?: {
    direction: "up" | "down" | "stable";
    label: string;
  };
}

const accentStyles = {
  olive:  { icon: "#385E31", iconBg: "#EFF5EE", iconBorder: "#CDE0CB", value: "#1C281A" },
  blue:   { icon: "#385E31", iconBg: "#EFF5EE", iconBorder: "#CDE0CB", value: "#1C281A" },
  cyan:   { icon: "#385E31", iconBg: "#EFF5EE", iconBorder: "#CDE0CB", value: "#1C281A" },
  green:  { icon: "#2E7D32", iconBg: "#E8F5E9", iconBorder: "#A5D6A7", value: "#1C281A" },
  gold:   { icon: "#D98E04", iconBg: "#FEF7E8", iconBorder: "#FDE68A", value: "#1C281A" },
  amber:  { icon: "#E65100", iconBg: "#FFF3E0", iconBorder: "#FFCC80", value: "#1C281A" },
  red:    { icon: "#C62828", iconBg: "#FFEBEE", iconBorder: "#EF9A9A", value: "#1C281A" },
  violet: { icon: "#5C4A72", iconBg: "#F4EFF8", iconBorder: "#D4C7DF", value: "#1C281A" },
};

const trendColors = {
  up: "#2E7D32",
  down: "#C62828",
  stable: "#728070",
};

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  icon,
  accentColor = "olive",
  trend,
}) => {
  const accent = accentStyles[accentColor] || accentStyles.olive;

  return (
    <div
      className="card p-5 transition-all duration-200 group cursor-default"
      style={{ borderRadius: "12px", background: "#FFFFFF", border: "1px solid #E1E8DF" }}
    >
      <div className="flex items-start justify-between mb-3">
        <p
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: "#728070" }}
        >
          {label}
        </p>
        {icon && (
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 transition-transform group-hover:scale-105"
            style={{
              background: accent.iconBg,
              border: `1px solid ${accent.iconBorder}`,
              color: accent.icon,
            }}
          >
            {icon}
          </div>
        )}
      </div>

      <div
        className="text-2xl font-bold mb-1"
        style={{ color: accent.value }}
      >
        {value}
      </div>

      {subtext && (
        <p className="text-xs" style={{ color: "#728070" }}>{subtext}</p>
      )}

      {trend && (
        <div
          className="mt-3 pt-3 flex items-center gap-1.5 text-xs font-medium"
          style={{ borderTop: "1px solid #F0F4EF" }}
        >
          <span style={{ color: trendColors[trend.direction] }}>
            {trend.direction === "up" ? "↑" : trend.direction === "down" ? "↓" : "→"}{" "}
            {trend.label}
          </span>
        </div>
      )}
    </div>
  );
};
