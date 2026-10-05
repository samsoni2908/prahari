"use client";

import React from "react";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger" | "brass";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = "primary",
      size = "md",
      loading = false,
      icon,
      iconPosition = "left",
      className = "",
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium transition-all duration-150 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none active:scale-[0.98]";

    const variantStyles = {
      primary:
        "bg-[#2C5127] text-white hover:bg-[#1E3A1A] active:bg-[#152B12] shadow-sm shadow-[#2C5127]/20 border border-[#244320]",
      secondary:
        "bg-[#F4F1EA] text-[#182417] hover:bg-[#EAE5DA] active:bg-[#E0DACD] border border-[#D0DCD0]",
      outline:
        "bg-white text-[#2C5127] border border-[#CFDDCE] hover:bg-[#F6F7F3] hover:border-[#2C5127]",
      ghost:
        "bg-transparent text-[#3B4B3A] hover:bg-[#F6F7F3] hover:text-[#182417]",
      danger:
        "bg-[#B91C1C] text-white hover:bg-[#991B1B] active:bg-[#7F1D1D] shadow-sm shadow-red-800/20 border border-red-800",
      brass:
        "bg-[#B8860B] text-white hover:bg-[#996515] active:bg-[#7A5012] shadow-sm shadow-amber-800/20 border border-[#8C6609]",
    };

    const sizeStyles = {
      sm: "text-xs px-2.5 py-1.5 gap-1.5",
      md: "text-xs md:text-sm px-3.5 py-2 gap-2",
      lg: "text-sm md:text-base px-5 py-2.5 gap-2.5 font-semibold",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin shrink-0" />
        ) : (
          icon && iconPosition === "left" && <span className="shrink-0">{icon}</span>
        )}
        <span>{children}</span>
        {!loading && icon && iconPosition === "right" && (
          <span className="shrink-0">{icon}</span>
        )}
      </button>
    );
  }
);
Button.displayName = "Button";

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  "aria-label": string;
}

export const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  (
    {
      children,
      variant = "ghost",
      size = "md",
      loading = false,
      className = "",
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 disabled:opacity-50 disabled:pointer-events-none";

    const variantStyles = {
      primary: "bg-[#2C5127] text-white hover:bg-[#1E3A1A]",
      secondary: "bg-[#F4F1EA] text-[#182417] hover:bg-[#EAE5DA] border border-[#D0DCD0]",
      outline: "bg-white text-[#2C5127] border border-[#CFDDCE] hover:bg-[#F6F7F3]",
      ghost: "text-[#677766] hover:bg-[#F6F7F3] hover:text-[#182417]",
      danger: "text-[#B91C1C] hover:bg-[#FEF2F2]",
    };

    const sizeStyles = {
      sm: "h-7 w-7 text-xs",
      md: "h-9 w-9 text-sm",
      lg: "h-11 w-11 text-base",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : children}
      </button>
    );
  }
);
IconButton.displayName = "IconButton";
