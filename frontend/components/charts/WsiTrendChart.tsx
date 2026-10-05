"use client";

import React, { useState } from "react";

interface DataPoint {
  date: string;
  wsi: number;
  d?: number;
  r?: number;
  n?: number;
}

interface WsiTrendChartProps {
  data: DataPoint[];
  height?: number;
}

export default function WsiTrendChart({ data, height = 240 }: WsiTrendChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!data || data.length === 0) {
    return (
      <div className="h-60 flex items-center justify-center text-xs text-[#677766] bg-[#FAF9F5] rounded-xl border border-[#CFDDCE]">
        Insufficient historical WSI data to render trend curve
      </div>
    );
  }

  const paddingLeft = 40;
  const paddingRight = 20;
  const paddingTop = 20;
  const paddingBottom = 30;
  const width = 640;

  const chartWidth = width - paddingLeft - paddingRight;
  const chartHeight = height - paddingTop - paddingBottom;

  // Scales
  const minY = 0;
  const maxY = 100;

  const getX = (index: number) => paddingLeft + (index / (data.length - 1 || 1)) * chartWidth;
  const getY = (val: number) => paddingTop + chartHeight - ((val - minY) / (maxY - minY)) * chartHeight;

  // Build SVG path
  const points = data.map((d, i) => `${getX(i)},${getY(d.wsi)}`).join(" ");
  const areaPath = `M ${getX(0)},${paddingTop + chartHeight} L ${points} L ${getX(data.length - 1)},${paddingTop + chartHeight} Z`;
  const linePath = `M ${points}`;

  const activePoint = hoveredIdx !== null ? data[hoveredIdx] : data[data.length - 1];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-4 flex-wrap">
          <span className="flex items-center gap-1.5 text-[#3B4B3A] font-medium">
            <span className="h-2.5 w-2.5 rounded-full bg-[#2C5127]" />
            <span>WSI Trend (Mean EWMA)</span>
          </span>
          <span className="flex items-center gap-1.5 text-[#15803D]">
            <span className="h-2 w-2 rounded-full bg-[#15803D]" />
            <span>LOW (0–39)</span>
          </span>
          <span className="flex items-center gap-1.5 text-[#B45309]">
            <span className="h-2 w-2 rounded-full bg-[#B45309]" />
            <span>MEDIUM (40–69)</span>
          </span>
          <span className="flex items-center gap-1.5 text-[#B91C1C]">
            <span className="h-2 w-2 rounded-full bg-[#B91C1C]" />
            <span>HIGH (70–100)</span>
          </span>
        </div>
        {activePoint && (
          <div className="font-mono text-xs text-[#182417] bg-[#FAF9F5] px-2.5 py-1 rounded-lg border border-[#CFDDCE]">
            Date: <span className="font-semibold">{activePoint.date}</span> • WSI:{" "}
            <span className="font-bold text-[#2C5127]">{activePoint.wsi}</span>
          </div>
        )}
      </div>

      <div className="relative w-full overflow-hidden rounded-xl bg-white border border-[#CFDDCE] p-3 shadow-sm">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible select-none"
        >
          <defs>
            <linearGradient id="wsiOliveGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2C5127" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#2C5127" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 20, 40, 70, 100].map((val) => {
            const y = getY(val);
            const is70 = val === 70;
            const is40 = val === 40;
            return (
              <g key={val}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={width - paddingRight}
                  y2={y}
                  stroke={is70 ? "#B91C1C" : is40 ? "#B45309" : "#E4ECE3"}
                  strokeWidth={is70 || is40 ? 1 : 1}
                  strokeDasharray={is70 || is40 ? "4 4" : undefined}
                  opacity={is70 || is40 ? 0.7 : 0.9}
                />
                <text
                  x={paddingLeft - 8}
                  y={y + 3}
                  textAnchor="end"
                  fill={is70 ? "#B91C1C" : is40 ? "#B45309" : "#677766"}
                  fontSize="10"
                  fontFamily="monospace"
                  fontWeight={is70 || is40 ? "bold" : "normal"}
                >
                  {val}
                </text>
              </g>
            );
          })}

          {/* Area Fill */}
          <path d={areaPath} fill="url(#wsiOliveGradient)" />

          {/* Line Path */}
          <path
            d={linePath}
            fill="none"
            stroke="#2C5127"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Interactive Nodes */}
          {data.map((d, i) => {
            const cx = getX(i);
            const cy = getY(d.wsi);
            const isHovered = hoveredIdx === i;
            return (
              <g
                key={i}
                onMouseEnter={() => setHoveredIdx(i)}
                onMouseLeave={() => setHoveredIdx(null)}
                className="cursor-pointer"
              >
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 5.5 : 3}
                  fill={isHovered ? "#1E3A1A" : "#2C5127"}
                  stroke="#FFFFFF"
                  strokeWidth="1.5"
                />
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
