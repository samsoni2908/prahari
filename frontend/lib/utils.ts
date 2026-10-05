// Frontend UI Utilities
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRiskBand(score: number): {
  band: "LOW" | "MEDIUM" | "HIGH";
  colorClass: string;
  bgClass: string;
  borderClass: string;
} {
  if (score >= 70) {
    return {
      band: "HIGH",
      colorClass: "text-state-critical",
      bgClass: "bg-state-critical-bg",
      borderClass: "border-state-critical/40",
    };
  }
  if (score >= 40) {
    return {
      band: "MEDIUM",
      colorClass: "text-state-warning",
      bgClass: "bg-state-warning-bg",
      borderClass: "border-state-warning/40",
    };
  }
  return {
    band: "LOW",
    colorClass: "text-state-normal",
    bgClass: "bg-state-normal-bg",
    borderClass: "border-state-normal/40",
  };
}
