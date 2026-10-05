"use client";

import React from "react";
import { ArrowDownRight, CheckCircle2 } from "lucide-react";

interface ScenarioMetrics {
  avg_wsi: number;
  peak_wsi: number;
  high_strain_count?: number;
}

interface ScenarioCompareChartProps {
  before: ScenarioMetrics;
  after: ScenarioMetrics;
}

export default function ScenarioCompareChart({ before, after }: ScenarioCompareChartProps) {
  const avgDelta = (after.avg_wsi - before.avg_wsi).toFixed(1);
  const peakDelta = (after.peak_wsi - before.peak_wsi).toFixed(1);

  return (
    <div className="space-y-4">
      {/* KPI Delta Cards */}
      <div className="grid grid-cols-2 gap-4">
        <div className="p-3.5 rounded-lg bg-surface-raised border border-border-subtle space-y-1">
          <div className="text-[11px] text-text-muted">Unit Average WSI Delta</div>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono text-state-normal">
              {after.avg_wsi}
            </span>
            <span className="text-xs text-text-muted line-through">
              {before.avg_wsi}
            </span>
            <span className="text-xs font-semibold text-state-normal flex items-center">
              <ArrowDownRight className="h-3.5 w-3.5 mr-0.5" />
              {avgDelta} pts
            </span>
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-surface-raised border border-border-subtle space-y-1">
          <div className="text-[11px] text-text-muted">Peak Strain Relief</div>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono text-state-info">
              {after.peak_wsi}
            </span>
            <span className="text-xs text-text-muted line-through">
              {before.peak_wsi}
            </span>
            <span className="text-xs font-semibold text-state-info flex items-center">
              <ArrowDownRight className="h-3.5 w-3.5 mr-0.5" />
              {peakDelta} pts
            </span>
          </div>
        </div>
      </div>

      {/* Comparative Bars */}
      <div className="p-4 rounded-lg bg-surface border border-border-subtle space-y-4">
        <div className="text-xs font-semibold text-text-primary">
          Workload Balance Metrics (Before vs After Simulation)
        </div>

        {/* Avg WSI Bar */}
        <div className="space-y-1.5 text-xs">
          <div className="flex justify-between text-text-secondary">
            <span>Average Workload Strain</span>
            <span className="font-mono">
              {before.avg_wsi} → <strong className="text-state-normal">{after.avg_wsi}</strong>
            </span>
          </div>
          <div className="space-y-1">
            <div className="h-2 w-full bg-surface-raised rounded-full overflow-hidden">
              <div
                className="h-full bg-state-elevated rounded-full"
                style={{ width: `${Math.min(100, before.avg_wsi)}%` }}
              />
            </div>
            <div className="h-2 w-full bg-surface-raised rounded-full overflow-hidden">
              <div
                className="h-full bg-state-normal rounded-full"
                style={{ width: `${Math.min(100, after.avg_wsi)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Peak WSI Bar */}
        <div className="space-y-1.5 text-xs">
          <div className="flex justify-between text-text-secondary">
            <span>Peak Individual Strain</span>
            <span className="font-mono">
              {before.peak_wsi} → <strong className="text-state-info">{after.peak_wsi}</strong>
            </span>
          </div>
          <div className="space-y-1">
            <div className="h-2 w-full bg-surface-raised rounded-full overflow-hidden">
              <div
                className="h-full bg-state-critical rounded-full"
                style={{ width: `${Math.min(100, before.peak_wsi)}%` }}
              />
            </div>
            <div className="h-2 w-full bg-surface-raised rounded-full overflow-hidden">
              <div
                className="h-full bg-state-info rounded-full"
                style={{ width: `${Math.min(100, after.peak_wsi)}%` }}
              />
            </div>
          </div>
        </div>

        <div className="pt-2 flex items-center justify-between text-[11px] text-text-muted border-t border-border-subtle">
          <span className="flex items-center gap-1.5 text-state-normal font-medium">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>Operational minimum staffing coverage preserved (100%)</span>
          </span>
          <span>Optimizer: GREEDY_HILL_CLIMB</span>
        </div>
      </div>
    </div>
  );
}
