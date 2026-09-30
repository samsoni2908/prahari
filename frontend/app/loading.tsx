"use client";

import React from "react";

export default function Loading() {
  return (
    <div className="min-h-screen bg-prahari-bg flex flex-col items-center justify-center p-6 text-prahari-textPrimary">
      <div className="relative flex items-center justify-center mb-6">
        <div className="w-16 h-16 border-2 border-prahari-oliveBorder rounded-full animate-ping absolute"></div>
        <div className="w-12 h-12 border-2 border-prahari-olive border-t-transparent rounded-full animate-spin"></div>
        <div className="w-4 h-4 bg-prahari-gold rounded-full shadow-[0_0_12px_rgba(212,175,55,0.4)]"></div>
      </div>
      <div className="text-center space-y-2">
        <h2 className="text-lg font-semibold tracking-wider text-prahari-oliveDark uppercase font-mono">
          PRAHARI System Initializing
        </h2>
        <p className="text-xs text-prahari-textMuted font-mono tracking-wide">
          Verifying operational clearance and establishing secure session...
        </p>
      </div>
    </div>
  );
}
