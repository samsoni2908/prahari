"use client";

import React from "react";
import { Loader2, AlertCircle, Inbox, HelpCircle, RefreshCw } from "lucide-react";
import { Button } from "./Button";

export const LoadingState: React.FC<{
  title?: string;
  description?: string;
  className?: string;
}> = ({ title = "Loading telemetry...", description, className = "" }) => {
  return (
    <div
      className={`min-h-[220px] flex flex-col items-center justify-center p-6 text-center bg-white rounded-xl border border-[#CFDDCE] ${className}`}
    >
      <Loader2 className="h-7 w-7 text-[#2C5127] animate-spin mb-3" />
      <h4 className="text-sm font-semibold text-[#182417]">{title}</h4>
      {description && (
        <p className="mt-1 text-xs text-[#677766] max-w-sm">{description}</p>
      )}
    </div>
  );
};

export const EmptyState: React.FC<{
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}> = ({ icon, title, description, action, className = "" }) => {
  return (
    <div
      className={`min-h-[220px] flex flex-col items-center justify-center p-6 text-center bg-white rounded-xl border border-[#CFDDCE] ${className}`}
    >
      <div className="h-12 w-12 rounded-xl bg-[#F6F7F3] border border-[#CFDDCE] text-[#677766] flex items-center justify-center mb-3">
        {icon || <Inbox className="h-6 w-6" />}
      </div>
      <h4 className="text-sm font-semibold text-[#182417]">{title}</h4>
      <p className="mt-1 text-xs text-[#677766] max-w-sm">{description}</p>
      {action && (
        <div className="mt-4">
          <Button variant="secondary" size="sm" onClick={action.onClick}>
            {action.label}
          </Button>
        </div>
      )}
    </div>
  );
};

export const ErrorState: React.FC<{
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}> = ({
  title = "Operational Data Sync Error",
  message,
  onRetry,
  className = "",
}) => {
  return (
    <div
      className={`min-h-[200px] flex flex-col items-center justify-center p-6 text-center bg-[#FEF2F2] rounded-xl border border-[#FECACA] ${className}`}
    >
      <div className="h-10 w-10 rounded-full bg-white text-[#B91C1C] flex items-center justify-center mb-3 shadow-sm border border-[#FECACA]">
        <AlertCircle className="h-5 w-5" />
      </div>
      <h4 className="text-sm font-bold text-[#B91C1C]">{title}</h4>
      <p className="mt-1 text-xs text-[#7F1D1D] max-w-md">{message}</p>
      {onRetry && (
        <div className="mt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            icon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            Retry Connection
          </Button>
        </div>
      )}
    </div>
  );
};

export const UnavailableState: React.FC<{
  title?: string;
  reason?: string;
  code?: "INSUFFICIENT_HISTORY" | "MODEL_UNAVAILABLE" | "DATA_STALE" | "NOT_COMPUTED" | string;
  className?: string;
}> = ({
  title = "Telemetry Unavailable",
  reason = "Baseline requires minimum 14 days of operational service records.",
  code = "INSUFFICIENT_HISTORY",
  className = "",
}) => {
  return (
    <div
      className={`min-h-[160px] flex flex-col items-center justify-center p-5 text-center bg-[#F6F7F3] rounded-xl border border-dashed border-[#CFDDCE] ${className}`}
    >
      <HelpCircle className="h-5 w-5 text-[#9AA899] mb-2" />
      <span className="text-[10px] font-mono font-bold text-[#677766] uppercase tracking-wider mb-1">
        {code}
      </span>
      <h5 className="text-xs font-semibold text-[#182417]">{title}</h5>
      <p className="mt-0.5 text-[11px] text-[#677766] max-w-xs">{reason}</p>
    </div>
  );
};

export const Skeleton: React.FC<{
  className?: string;
  width?: string | number;
  height?: string | number;
}> = ({ className = "", width, height }) => {
  return (
    <div
      style={{ width, height }}
      className={`animate-pulse bg-[#E4ECE3] rounded-md ${className}`}
    />
  );
};
