"use client";

import React from "react";

interface RiskDistributionChartProps {
  low: number;
  medium: number;
  high: number;
}

export const RiskDistributionChart: React.FC<RiskDistributionChartProps> = ({
  low = 0,
  medium = 0,
  high = 0,
}) => {
  const total = low + medium + high;
  const safeTotal = total > 0 ? total : 1;

  const lowPct = Math.round((low / safeTotal) * 100);
  const medPct = Math.round((medium / safeTotal) * 100);
  const highPct = Math.round((high / safeTotal) * 100);

  const radius = 56;
  const circumference = 2 * Math.PI * radius;

  const lowStroke = (low / safeTotal) * circumference;
  const medStroke = (medium / safeTotal) * circumference;
  const highStroke = (high / safeTotal) * circumference;

  const lowOffset = 0;
  const medOffset = -lowStroke;
  const highOffset = -(lowStroke + medStroke);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-around gap-6">
      {/* SVG Donut */}
      <div className="relative w-40 h-40 flex items-center justify-center shrink-0">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 140 140">
          {/* Background track */}
          <circle cx="70" cy="70" r={radius} fill="transparent" stroke="#E2E8F0" strokeWidth="14" />

          {/* LOW (green) */}
          {low > 0 && (
            <circle
              cx="70" cy="70" r={radius}
              fill="transparent"
              stroke="#4CAF50"
              strokeWidth="14"
              strokeDasharray={`${lowStroke} ${circumference}`}
              strokeDashoffset={lowOffset}
              style={{ transition: "stroke-dashoffset 0.7s ease" }}
            />
          )}

          {/* MEDIUM (amber) */}
          {medium > 0 && (
            <circle
              cx="70" cy="70" r={radius}
              fill="transparent"
              stroke="#FF9800"
              strokeWidth="14"
              strokeDasharray={`${medStroke} ${circumference}`}
              strokeDashoffset={medOffset}
              style={{ transition: "stroke-dashoffset 0.7s ease" }}
            />
          )}

          {/* HIGH (red) */}
          {high > 0 && (
            <circle
              cx="70" cy="70" r={radius}
              fill="transparent"
              stroke="#F44336"
              strokeWidth="14"
              strokeDasharray={`${highStroke} ${circumference}`}
              strokeDashoffset={highOffset}
              style={{ transition: "stroke-dashoffset 0.7s ease" }}
            />
          )}
        </svg>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-2xl font-bold text-prahari-textPrimary">{total}</span>
          <span className="text-[10px] text-prahari-textMuted uppercase font-semibold tracking-wider">
            Monitored
          </span>
        </div>
      </div>

      {/* Legend & Breakdown */}
      <div className="flex flex-col gap-3 min-w-[160px] w-full sm:w-auto">
        {/* LOW */}
        <div className="flex items-center justify-between gap-4 p-2 rounded-lg bg-green-50/60 border border-green-100">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-green-500 shrink-0" />
            <span className="text-xs font-semibold text-green-900">Stable (Low)</span>
          </div>
          <div className="text-right">
            <span className="text-xs font-bold text-green-900 mr-1.5">{low}</span>
            <span className="text-[10px] text-green-700">({lowPct}%)</span>
          </div>
        </div>

        {/* MEDIUM */}
        <div className="flex items-center justify-between gap-4 p-2 rounded-lg bg-amber-50/60 border border-amber-100">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
            <span className="text-xs font-semibold text-amber-900">Watch (Med)</span>
          </div>
          <div className="text-right">
            <span className="text-xs font-bold text-amber-900 mr-1.5">{medium}</span>
            <span className="text-[10px] text-amber-700">({medPct}%)</span>
          </div>
        </div>

        {/* HIGH */}
        <div className="flex items-center justify-between gap-4 p-2 rounded-lg bg-red-50/60 border border-red-100">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 shrink-0" />
            <span className="text-xs font-semibold text-red-900">Attention (High)</span>
          </div>
          <div className="text-right">
            <span className="text-xs font-bold text-red-900 mr-1.5">{high}</span>
            <span className="text-[10px] text-red-700">({highPct}%)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
