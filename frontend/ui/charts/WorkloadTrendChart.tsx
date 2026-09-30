"use client";

import React from "react";

interface DataPoint {
  label: string;
  hours: number;
}

interface WorkloadTrendChartProps {
  data?: DataPoint[];
}

export const WorkloadTrendChart: React.FC<WorkloadTrendChartProps> = ({
  data = [
    { label: "Mon", hours: 8 },
    { label: "Tue", hours: 8.5 },
    { label: "Wed", hours: 10 },
    { label: "Thu", hours: 9 },
    { label: "Fri", hours: 11 },
    { label: "Sat", hours: 8 },
    { label: "Sun", hours: 7.5 },
  ],
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="w-full h-36 flex items-center justify-center text-sm text-prahari-textMuted">
        No workload shift data available for this period.
      </div>
    );
  }

  const maxVal = Math.max(...data.map((d) => Number(d.hours) || 0), 12);
  const maxHours = Math.ceil(maxVal * 1.2);
  const height = 140;
  const width = 420;
  const paddingX = 20;
  const paddingY = 24;

  const chartWidth = width - paddingX * 2;
  const chartHeight = height - paddingY * 2;

  // Threshold line at 10h
  const thresholdY = height - paddingY - (10 / maxHours) * chartHeight;

  const points = data.map((d, idx) => {
    const hours = Number(d.hours) || 0;
    const x = paddingX + (idx / Math.max(data.length - 1, 1)) * chartWidth;
    const y = height - paddingY - (hours / maxHours) * chartHeight;
    return { x, y, ...d, hours };
  });

  const pathD = points.reduce((acc, pt, i) =>
    i === 0 ? `M ${pt.x},${pt.y}` : `${acc} L ${pt.x},${pt.y}`, ""
  );

  const areaD = `${pathD} L ${points[points.length - 1].x},${height - paddingY} L ${points[0].x},${height - paddingY} Z`;

  return (
    <div className="w-full overflow-x-auto">
      <div className="min-w-[340px]">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto"
          style={{ overflow: "visible" }}
        >
          <defs>
            <linearGradient id="workloadAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#385E31" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#385E31" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line
            x1={paddingX} y1={paddingY}
            x2={width - paddingX} y2={paddingY}
            stroke="#F0F4EF" strokeWidth="1"
          />
          <line
            x1={paddingX} y1={height - paddingY}
            x2={width - paddingX} y2={height - paddingY}
            stroke="#E1E8DF" strokeWidth="1"
          />

          {/* 10h Warning Threshold dashed line */}
          <line
            x1={paddingX} y1={thresholdY}
            x2={width - paddingX} y2={thresholdY}
            stroke="#E65100" strokeWidth="1" strokeDasharray="4 3" opacity="0.75"
          />
          <text
            x={width - paddingX - 4} y={thresholdY - 4}
            textAnchor="end" fontSize="9" fill="#E65100" fontWeight="600" opacity="0.9"
          >
            10h Fatigue Limit
          </text>

          {/* Shaded Area */}
          <path d={areaD} fill="url(#workloadAreaGrad)" />

          {/* Line */}
          <path
            d={pathD}
            fill="none"
            stroke="#385E31"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data points & labels */}
          {points.map((pt, i) => {
            const isHigh = pt.hours >= 10;
            return (
              <g key={i}>
                <circle
                  cx={pt.x} cy={pt.y} r={isHigh ? "4" : "3"}
                  fill={isHigh ? "#E65100" : "#385E31"}
                  stroke="#FFFFFF" strokeWidth="1.5"
                />
                {/* Hours value above node */}
                <text
                  x={pt.x} y={pt.y - 7}
                  textAnchor="middle" fontSize="9"
                  fill={isHigh ? "#C62828" : "#465444"}
                  fontWeight={isHigh ? "700" : "500"}
                >
                  {pt.hours}h
                </text>
                {/* Day label on X axis */}
                <text
                  x={pt.x} y={height - 8}
                  textAnchor="middle" fontSize="10"
                  fill="#728070" fontWeight="500"
                >
                  {pt.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};
