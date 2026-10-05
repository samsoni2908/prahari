"use client";

import React from "react";

interface CohortBucket {
  label: string;
  count: number;
  color: string;
}

interface WsiDonutChartProps {
  buckets: CohortBucket[];
  totalPersonnel: number;
}

export default function WsiDonutChart({ buckets, totalPersonnel }: WsiDonutChartProps) {
  const safeTotal = totalPersonnel || 1;
  const radius = 68;
  const strokeWidth = 22;
  const circumference = 2 * Math.PI * radius;

  let accumulatedPercent = 0;

  // Harmonized palette mapping for bands
  const getSliceColor = (rawColor: string, label: string) => {
    const l = (label || "").toUpperCase();
    if (l.includes("LOW") || l.includes("STABLE")) return "#15803D";
    if (l.includes("MED") || l.includes("WATCH")) return "#B45309";
    if (l.includes("HIGH") || l.includes("ATTENTION") || l.includes("CRITICAL")) return "#B91C1C";
    return rawColor || "#677766";
  };

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-6 p-4 rounded-xl bg-white border border-[#CFDDCE] shadow-sm">
      {/* SVG Donut */}
      <div className="relative flex items-center justify-center shrink-0">
        <svg width="170" height="170" viewBox="0 0 170 170" className="rotate-[-90deg]">
          {/* Background circle track */}
          <circle
            cx="85"
            cy="85"
            r={radius}
            fill="transparent"
            stroke="#E4ECE3"
            strokeWidth={strokeWidth}
          />
          {/* Slices */}
          {buckets.map((b, idx) => {
            const pct = b.count / safeTotal;
            const strokeDasharray = `${pct * circumference} ${circumference}`;
            const strokeDashoffset = -accumulatedPercent * circumference;
            accumulatedPercent += pct;
            const sliceColor = getSliceColor(b.color, b.label);

            return (
              <circle
                key={idx}
                cx="85"
                cy="85"
                r={radius}
                fill="transparent"
                stroke={sliceColor}
                strokeWidth={strokeWidth}
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="butt"
              />
            );
          })}
        </svg>

        {/* Center Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center select-none pointer-events-none">
          <span className="text-2xl font-bold font-mono text-[#182417]">
            {totalPersonnel}
          </span>
          <span className="text-[10px] text-[#677766] uppercase tracking-wider font-semibold font-mono">
            Troops
          </span>
        </div>
      </div>

      {/* Legend / Stats */}
      <div className="flex-1 w-full space-y-2 text-xs">
        {buckets.map((b, idx) => {
          const pct = Math.round((b.count / safeTotal) * 100);
          const sliceColor = getSliceColor(b.color, b.label);
          return (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 rounded-lg bg-[#FAF9F5] border border-[#CFDDCE]"
            >
              <div className="flex items-center gap-2.5">
                <span
                  className="h-3 w-3 rounded-full shrink-0"
                  style={{ backgroundColor: sliceColor }}
                />
                <span className="text-[#182417] font-medium">{b.label}</span>
              </div>
              <div className="font-mono text-right">
                <span className="font-bold text-[#182417]">{b.count}</span>{" "}
                <span className="text-[11px] text-[#677766]">({pct}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
