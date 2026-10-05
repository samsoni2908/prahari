"use client";

import React from "react";
import Image from "next/image";
import { TrendingUp, TrendingDown, Minus, ArrowRight } from "lucide-react";

export interface StatCardProps {
  title: string;
  value: React.ReactNode;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    direction: "up" | "down" | "neutral";
    value: string;
    label?: string;
  };
  status?: "normal" | "elevated" | "critical" | "neutral";
  unavailable?: boolean;
  unavailableText?: string;
  className?: string;
  onClick?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  status = "neutral",
  unavailable = false,
  unavailableText = "Not Computed",
  className = "",
  onClick,
}) => {
  const statusBorder = {
    normal: "border-l-4 border-l-[#15803D]",
    elevated: "border-l-4 border-l-[#B45309]",
    critical: "border-l-4 border-l-[#B91C1C]",
    neutral: "",
  }[status];

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl p-4 md:p-5 border border-[#CFDDCE] shadow-sm hover:shadow-md transition-all ${statusBorder} ${
        onClick ? "cursor-pointer hover:border-[#2C5127]" : ""
      } ${className}`}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#677766]">
          {title}
        </span>
        {icon && (
          <div className="h-8 w-8 rounded-lg bg-[#EAF1E9] text-[#2C5127] flex items-center justify-center shrink-0">
            {icon}
          </div>
        )}
      </div>

      <div className="mt-2.5 flex items-baseline gap-2">
        {unavailable ? (
          <span className="text-sm font-mono font-medium text-[#9AA899] italic">
            {unavailableText}
          </span>
        ) : (
          <div className="text-2xl md:text-3xl font-extrabold text-[#182417] tracking-tight">
            {value}
          </div>
        )}
      </div>

      {(subtitle || trend) && (
        <div className="mt-2.5 flex items-center justify-between text-xs text-[#677766]">
          {subtitle && <span className="truncate">{subtitle}</span>}
          {trend && (
            <span
              className={`inline-flex items-center gap-1 font-mono font-medium ${
                trend.direction === "up"
                  ? "text-[#15803D]"
                  : trend.direction === "down"
                  ? "text-[#B91C1C]"
                  : "text-[#677766]"
              }`}
            >
              {trend.direction === "up" && <TrendingUp className="h-3.5 w-3.5" />}
              {trend.direction === "down" && <TrendingDown className="h-3.5 w-3.5" />}
              {trend.direction === "neutral" && <Minus className="h-3.5 w-3.5" />}
              <span>{trend.value}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export interface FeatureCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  tag?: string;
  className?: string;
}

export const FeatureCard: React.FC<FeatureCardProps> = ({
  title,
  description,
  icon,
  tag,
  className = "",
}) => {
  return (
    <div
      className={`bg-white rounded-2xl p-6 border border-[#CFDDCE] shadow-sm hover:shadow-cardHover transition-all duration-200 group ${className}`}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="h-12 w-12 rounded-xl bg-[#EAF1E9] border border-[#CFDDCE] text-[#2C5127] flex items-center justify-center group-hover:scale-105 transition-transform">
          {icon}
        </div>
        {tag && (
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-[#FAF9F5] text-[#2C5127] border border-[#CFDDCE]">
            {tag}
          </span>
        )}
      </div>
      <h3 className="font-serif text-lg font-bold text-[#182417] tracking-tight group-hover:text-[#2C5127] transition-colors">
        {title}
      </h3>
      <p className="mt-2 text-xs md:text-sm text-[#3B4B3A] leading-relaxed">
        {description}
      </p>
    </div>
  );
};

export interface RoleCardProps {
  role: string;
  title: string;
  description: string;
  imageSrc: string;
  capabilities: string[];
  ctaLabel?: string;
  onSelect?: () => void;
}

export const RoleCard: React.FC<RoleCardProps> = ({
  role,
  title,
  description,
  imageSrc,
  capabilities,
  ctaLabel = "Access Role Portal",
  onSelect,
}) => {
  return (
    <div className="bg-white rounded-2xl border border-[#CFDDCE] shadow-card hover:shadow-cardHover overflow-hidden flex flex-col transition-all duration-300">
      <div className="relative h-44 w-full bg-[#1A3217] overflow-hidden">
        <Image
          src={imageSrc}
          alt={title}
          fill
          className="object-cover opacity-85 hover:scale-105 transition-transform duration-500"
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#1A3217]/90 via-[#1A3217]/40 to-transparent" />
        <div className="absolute top-3 left-3">
          <span className="text-[10px] font-mono font-bold px-2.5 py-1 rounded bg-black/60 text-white backdrop-blur-sm border border-white/20 uppercase tracking-widest">
            {role}
          </span>
        </div>
        <div className="absolute bottom-3 left-3 right-3 text-white">
          <h4 className="font-serif text-lg font-bold leading-tight drop-shadow-sm">
            {title}
          </h4>
        </div>
      </div>

      <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
        <p className="text-xs text-[#3B4B3A] leading-relaxed">
          {description}
        </p>

        <div className="space-y-1.5 border-t border-[#E4ECE3] pt-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-[#677766]">
            Authorized Scope:
          </span>
          <ul className="text-xs space-y-1 text-[#182417]">
            {capabilities.map((cap, i) => (
              <li key={i} className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#2C5127] shrink-0" />
                <span className="truncate">{cap}</span>
              </li>
            ))}
          </ul>
        </div>

        {onSelect && (
          <button
            onClick={onSelect}
            className="w-full mt-2 py-2 px-3 rounded-lg bg-[#FAF9F5] hover:bg-[#2C5127] hover:text-white text-[#2C5127] font-medium text-xs border border-[#CFDDCE] hover:border-[#2C5127] transition-all flex items-center justify-center gap-1.5 group"
          >
            <span>{ctaLabel}</span>
            <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" />
          </button>
        )}
      </div>
    </div>
  );
};
