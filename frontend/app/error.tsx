"use client";

import React, { useEffect } from "react";
import Link from "next/link";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log exception safely without leaking PII
    console.error("SWASTI UI Exception:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-prahari-bg flex flex-col items-center justify-center p-6 text-prahari-textPrimary">
      <div className="w-full max-w-md bg-white border border-red-200 rounded-xl p-8 shadow-card text-center space-y-6">
        <div className="w-14 h-14 bg-red-50 border border-red-200 rounded-full flex items-center justify-center mx-auto text-red-600">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>

        <div>
          <h2 className="text-xl font-bold tracking-wider text-prahari-oliveDark uppercase font-mono">
            Operational Service Notice
          </h2>
          <p className="mt-2 text-sm text-prahari-textMuted">
            A temporary system anomaly was detected while loading this view. Authorization integrity remains intact.
          </p>
          {error.digest && (
            <p className="mt-2 text-xs font-mono text-prahari-textMuted">
              Reference Code: {error.digest}
            </p>
          )}
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <button
            onClick={() => reset()}
            className="w-full sm:w-auto px-5 py-2.5 bg-prahari-olive hover:bg-prahari-oliveDark text-white font-semibold text-sm rounded-lg transition-all shadow-sm font-mono"
          >
            Retry Operation
          </button>
          <Link
            href="/"
            className="w-full sm:w-auto px-5 py-2.5 bg-prahari-surface hover:bg-prahari-surfaceHighlight text-prahari-textPrimary font-medium text-sm rounded-lg border border-prahari-border transition-all font-mono text-center"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
