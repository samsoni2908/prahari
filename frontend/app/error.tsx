"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { AlertCircle, RefreshCw, ArrowLeft } from "lucide-react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log exception safely without leaking PII
    console.error("PRAHARI UI Exception:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-[#FBFBF8] flex flex-col items-center justify-center p-6 text-[#182417]">
      <div className="w-full max-w-md bg-white border border-[#CFDDCE] rounded-2xl p-8 shadow-card text-center space-y-6">
        <div className="w-14 h-14 bg-[#FEF2F2] border border-[#FECACA] rounded-2xl flex items-center justify-center mx-auto text-[#B91C1C]">
          <AlertCircle className="w-8 h-8" />
        </div>

        <div className="space-y-2">
          <h2 className="font-serif text-xl font-bold tracking-tight text-[#182417]">
            Operational Service Notice
          </h2>
          <p className="text-xs text-[#677766] leading-relaxed">
            A temporary system anomaly was detected while loading this view. Authorization integrity remains intact.
          </p>
          {error.digest && (
            <p className="text-[11px] font-mono text-[#9AA899]">
              Reference Code: {error.digest}
            </p>
          )}
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <button
            onClick={() => reset()}
            className="w-full sm:w-auto px-5 py-2.5 bg-[#2C5127] hover:bg-[#1E3A1A] text-white font-semibold text-xs rounded-lg transition-all shadow-sm flex items-center justify-center gap-1.5"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Retry Operation</span>
          </button>
          <Link
            href="/"
            className="w-full sm:w-auto px-5 py-2.5 bg-[#FAF9F5] hover:bg-[#F3F2EB] text-[#182417] font-medium text-xs rounded-lg border border-[#CFDDCE] transition-all flex items-center justify-center gap-1.5"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Return to Overview</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
