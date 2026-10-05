"use client";

import React from "react";
import type { OperationalDriver } from "@/lib/api";

interface DriverBarChartProps {
  drivers: OperationalDriver[];
}

export default function DriverBarChart({ drivers }: DriverBarChartProps) {
  if (!drivers || drivers.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-[#677766] bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
        Operational drivers telemetry unavailable
      </div>
    );
  }

  return (
    <div className="space-y-3.5">
      {drivers.map((d) => {
        // Color coding by component severity
        const barColor =
          d.value !== null && d.value >= 75
            ? "#B91C1C"
            : d.value !== null && d.value >= 50
            ? "#B45309"
            : "#2C5127";

        return (
          <div key={d.code} className="space-y-1.5">
            <div className="flex justify-between items-center text-xs">
              <span className="text-[#3B4B3A] font-medium flex items-center gap-1.5">
                <span className="text-[#2C5127] font-mono font-bold">[{d.code}]</span>
                <span>{d.name}</span>
                <span className="text-[10px] text-[#677766] font-mono">
                  ({Math.round(d.weight * 100)}% wt)
                </span>
              </span>
              <span className="font-mono font-bold text-[#182417]">
                {d.value === null ? (
                  <span className="text-[#9AA899] italic font-normal">Pending</span>
                ) : (
                  <>
                    {d.value}{" "}
                    <span className="text-[10px] text-[#677766] font-normal">/ 100</span>
                  </>
                )}
              </span>
            </div>
            {d.value !== null && (
              <div className="h-2.5 w-full bg-[#FAF9F5] rounded-full overflow-hidden border border-[#CFDDCE]">
                <div
                  className="h-full rounded-full transition-all duration-500 ease-out"
                  style={{
                    width: `${Math.min(100, d.value)}%`,
                    backgroundColor: barColor,
                  }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
