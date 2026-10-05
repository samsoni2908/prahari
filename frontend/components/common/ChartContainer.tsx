"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus, Info } from "lucide-react";

export interface ChartContainerProps {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  legend?: React.ReactNode;
  children: React.ReactNode;
  footerNote?: string;
  className?: string;
}

export const ChartContainer: React.FC<ChartContainerProps> = ({
  title,
  subtitle,
  badge,
  actions,
  legend,
  children,
  footerNote,
  className = "",
}) => {
  return (
    <div
      className={`bg-white rounded-2xl border border-[#CFDDCE] shadow-sm p-4 md:p-6 space-y-4 ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#E4ECE3]">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-serif text-base font-bold text-[#182417]">
              {title}
            </h3>
            {badge}
          </div>
          {subtitle && (
            <p className="text-xs text-[#677766] mt-0.5">{subtitle}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>

      <div className="w-full overflow-hidden">{children}</div>

      {legend && (
        <div className="pt-2 border-t border-[#E4ECE3] flex items-center justify-center flex-wrap gap-4 text-xs text-[#3B4B3A]">
          {legend}
        </div>
      )}

      {footerNote && (
        <div className="text-[11px] text-[#677766] flex items-center gap-1.5 font-mono">
          <Info className="h-3 w-3 shrink-0" />
          <span>{footerNote}</span>
        </div>
      )}
    </div>
  );
};

export const ChartLegendItem: React.FC<{
  color: string;
  label: string;
  value?: string | number;
}> = ({ color, label, value }) => {
  return (
    <div className="inline-flex items-center gap-1.5 text-xs">
      <span
        style={{ backgroundColor: color }}
        className="w-2.5 h-2.5 rounded-full shrink-0"
      />
      <span className="text-[#3B4B3A]">{label}</span>
      {value !== undefined && (
        <span className="font-mono font-bold text-[#182417] ml-0.5">
          ({value})
        </span>
      )}
    </div>
  );
};

export const TrendIndicator: React.FC<{
  direction: "up" | "down" | "neutral";
  value: string;
  label?: string;
  inverted?: boolean; // if up is bad (e.g. strain rising)
}> = ({ direction, value, label, inverted = false }) => {
  const isBad = inverted ? direction === "up" : direction === "down";
  const isGood = inverted ? direction === "down" : direction === "up";

  const colorClass = isGood
    ? "text-[#15803D] bg-[#ECFDF5] border-[#A7F3D0]"
    : isBad
    ? "text-[#B91C1C] bg-[#FEF2F2] border-[#FECACA]"
    : "text-[#4B5563] bg-[#F3F4F6] border-[#E5E7EB]";

  return (
    <span
      className={`inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-full border ${colorClass}`}
    >
      {direction === "up" && <TrendingUp className="h-3 w-3" />}
      {direction === "down" && <TrendingDown className="h-3 w-3" />}
      {direction === "neutral" && <Minus className="h-3 w-3" />}
      <span>{value}</span>
      {label && <span className="opacity-75">({label})</span>}
    </span>
  );
};
