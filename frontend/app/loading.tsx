"use client";

import React from "react";
import { Shield } from "lucide-react";

export default function Loading() {
  return (
    <div className="min-h-screen bg-[#FBFBF8] flex flex-col items-center justify-center p-6 text-[#182417]">
      <div className="relative flex items-center justify-center mb-6">
        <div className="w-16 h-16 border-2 border-[#CFDDCE] rounded-full animate-ping absolute" />
        <div className="w-12 h-12 border-2 border-[#2C5127] border-t-transparent rounded-full animate-spin" />
        <div className="w-4 h-4 bg-[#B8860B] rounded-full shadow-[0_0_12px_rgba(184,134,11,0.5)]" />
      </div>
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-2">
          <Shield className="h-5 w-5 text-[#2C5127]" />
          <h2 className="font-serif text-lg font-bold tracking-wider text-[#182417] uppercase">
            PRAHARI Initializing
          </h2>
        </div>
        <p className="text-xs text-[#677766] font-mono tracking-wide">
          Verifying operational clearance and establishing secure session...
        </p>
      </div>
    </div>
  );
}
