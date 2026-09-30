import React from "react";
import clsx from "clsx";

interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className, style }) => (
  <div
    className={clsx("animate-pulse rounded", className)}
    style={{ background: "#E2E8F0", ...style }}
  />
);

export const SkeletonCard: React.FC = () => (
  <div className="card p-5" style={{ borderRadius: "12px" }}>
    <div className="flex items-start justify-between mb-3">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-9 w-9 rounded-lg" />
    </div>
    <Skeleton className="h-8 w-20 mb-2" />
    <Skeleton className="h-3 w-32" />
  </div>
);

interface SkeletonTableProps {
  rows?: number;
  cols?: number;
}

export const SkeletonTable: React.FC<SkeletonTableProps> = ({ rows = 4, cols = 4 }) => (
  <div>
    <div className="flex gap-4 pb-3 mb-2" style={{ borderBottom: "1px solid #E2E8F0" }}>
      {Array.from({ length: cols }).map((_, i) => (
        <Skeleton key={i} className="h-3 flex-1" />
      ))}
    </div>
    {Array.from({ length: rows }).map((_, row) => (
      <div key={row} className="flex gap-4 py-3" style={{ borderBottom: "1px solid #F0F4F8" }}>
        {Array.from({ length: cols }).map((_, col) => (
          <Skeleton key={col} className="h-4 flex-1" style={{ opacity: 0.7 - row * 0.1 }} />
        ))}
      </div>
    ))}
  </div>
);

export const SkeletonProfile: React.FC = () => (
  <div className="card p-6" style={{ borderRadius: "12px" }}>
    <div className="flex items-center gap-4 mb-6">
      <Skeleton className="h-16 w-16 rounded-full" />
      <div className="flex-1">
        <Skeleton className="h-5 w-40 mb-2" />
        <Skeleton className="h-3 w-28" />
      </div>
    </div>
    <div className="grid grid-cols-2 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="space-y-1.5">
          <Skeleton className="h-2.5 w-20" />
          <Skeleton className="h-4 w-32" />
        </div>
      ))}
    </div>
  </div>
);
