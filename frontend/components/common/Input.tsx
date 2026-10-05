"use client";

import React from "react";
import { Search, X } from "lucide-react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  prefixIcon?: React.ReactNode;
  suffixIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, helperText, error, prefixIcon, suffixIcon, className = "", id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-semibold tracking-wide uppercase text-[#3B4B3A]"
          >
            {label}
          </label>
        )}
        <div className="relative flex items-center">
          {prefixIcon && (
            <div className="absolute left-3 text-[#677766] pointer-events-none flex items-center">
              {prefixIcon}
            </div>
          )}
          <input
            id={inputId}
            ref={ref}
            className={`w-full bg-white text-[#182417] text-xs md:text-sm placeholder-[#9AA899] border rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-[#2C5127] focus:border-[#2C5127] disabled:bg-[#F3F2EB] disabled:text-[#9AA899] ${
              prefixIcon ? "pl-9" : "pl-3.5"
            } ${suffixIcon ? "pr-9" : "pr-3.5"} py-2 ${
              error ? "border-[#B91C1C] focus:ring-[#B91C1C]" : "border-[#CFDDCE]"
            } ${className}`}
            {...props}
          />
          {suffixIcon && (
            <div className="absolute right-3 text-[#677766] flex items-center">
              {suffixIcon}
            </div>
          )}
        </div>
        {error ? (
          <p className="text-[11px] text-[#B91C1C] font-medium">{error}</p>
        ) : helperText ? (
          <p className="text-[11px] text-[#677766]">{helperText}</p>
        ) : null}
      </div>
    );
  }
);
Input.displayName = "Input";

export interface SearchInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange"> {
  value: string;
  onChange: (value: string) => void;
  onClear?: () => void;
  placeholder?: string;
}

export const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  ({ value, onChange, onClear, placeholder = "Search...", className = "", ...props }, ref) => {
    return (
      <div className="relative flex items-center w-full">
        <Search className="absolute left-3 h-4 w-4 text-[#677766] pointer-events-none" />
        <input
          ref={ref}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`w-full bg-white text-[#182417] text-xs md:text-sm placeholder-[#9AA899] border border-[#CFDDCE] rounded-lg pl-9 pr-8 py-2 focus:outline-none focus:ring-2 focus:ring-[#2C5127] focus:border-[#2C5127] transition-all shadow-sm ${className}`}
          {...props}
        />
        {value && (
          <button
            type="button"
            onClick={() => {
              onChange("");
              if (onClear) onClear();
            }}
            className="absolute right-2.5 p-1 text-[#677766] hover:text-[#182417] rounded-full hover:bg-[#F3F2EB]"
            aria-label="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
    );
  }
);
SearchInput.displayName = "SearchInput";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options?: Array<{ value: string; label: string }>;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, children, className = "", id, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label
            htmlFor={selectId}
            className="block text-xs font-semibold tracking-wide uppercase text-[#3B4B3A]"
          >
            {label}
          </label>
        )}
        <select
          id={selectId}
          ref={ref}
          className={`w-full bg-white text-[#182417] text-xs md:text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#2C5127] focus:border-[#2C5127] transition-all cursor-pointer ${
            error ? "border-[#B91C1C]" : "border-[#CFDDCE]"
          } ${className}`}
          {...props}
        >
          {options
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))
            : children}
        </select>
        {error && <p className="text-[11px] text-[#B91C1C] font-medium">{error}</p>}
      </div>
    );
  }
);
Select.displayName = "Select";
