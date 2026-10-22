"use client";

import React, { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Shield,
  Lock,
  User,
  KeyRound,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Eye,
  EyeOff,
  ChevronLeft,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  // Use the AuthContext login so the shared user state is populated immediately
  // and role-based navigation is handled in one place (auth-context.tsx)
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!username || !password) {
      setError("Please provide both username and password.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // AuthProvider.login() sets context user state AND router.push() to role portal
      await login(username, password);
    } catch (err: any) {
      setError(err.message || "Authentication failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[#FAF9F5] text-[#182417] overflow-hidden">
      {/* Left Column: Visual & Defence Identity (Desktop) */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-[#1A3217] overflow-hidden flex-col justify-between p-12">
        <Image
          src="/prahari/images/hero-force.webp"
          alt="Defence personnel in mountain terrain"
          fill
          priority
          className="object-cover opacity-60"
          sizes="50vw"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#142612] via-[#1A3217]/50 to-transparent" />
        <div className="absolute inset-0 bg-topo-pattern opacity-10 pointer-events-none" />

        {/* Top Branding */}
        <div className="relative z-10">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-white/80 hover:text-white transition-colors text-xs font-mono mb-8"
          >
            <ChevronLeft className="h-4 w-4" />
            <span>Return to Overview</span>
          </Link>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-[#2C5127] border border-[#46723F] flex items-center justify-center text-white shadow-md">
              <Shield className="h-6 w-6 text-[#FAF9F5]" />
            </div>
            <div>
              <span className="font-serif text-2xl font-bold tracking-wider text-white">
                PRAHARI
              </span>
              <span className="ml-2 text-[10px] font-mono px-2 py-0.5 rounded bg-white/20 text-[#D8E2D6] border border-white/20">
                SIH 26186
              </span>
            </div>
          </div>
        </div>

        {/* Bottom Editorial Content */}
        <div className="relative z-10 space-y-4 max-w-lg">
          <div className="h-1 w-16 bg-[#B8860B] rounded-full" />
          <h2 className="font-serif text-3xl xl:text-4xl font-bold text-white leading-tight">
            Preserving Force Readiness Through Human-Centric Welfare Intelligence.
          </h2>
          <p className="text-sm text-[#D0E0CE] leading-relaxed">
            Privacy-preserving personnel welfare and operational workload/recovery
            decision support for CAPFs and Armed Forces.
          </p>

          <div className="pt-4 border-t border-white/15 flex items-center justify-between text-xs text-[#A6C3A0] font-mono">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-[#22C55E]" />
              <span>TLS / HttpOnly Sealed</span>
            </span>
            <span>Zero Raw Well-being to Command</span>
          </div>
        </div>
      </div>

      {/* Right Column: Authentication Card & Fast Fill */}
      <div className="flex-1 flex flex-col justify-center items-center px-6 sm:px-12 py-10 overflow-y-auto">
        <div className="max-w-md w-full space-y-6">
          {/* Mobile Back & Brand */}
          <div className="lg:hidden flex items-center justify-between pb-2 border-b border-[#CFDDCE]">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs text-[#677766] hover:text-[#182417] font-mono"
            >
              <ChevronLeft className="h-4 w-4" />
              <span>Back</span>
            </Link>
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-[#2C5127]" />
              <span className="font-serif text-sm font-bold text-[#182417]">PRAHARI</span>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-serif text-2xl md:text-3xl font-bold text-[#182417]">
                Portal Authentication
              </h1>
            </div>
            <p className="text-xs text-[#677766] mt-1">
              Enter your authorized Service ID and secure credential to access your designated role portal.
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-3.5 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-[#B91C1C] text-xs flex items-start gap-2.5 animate-in fade-in">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form action="javascript:void(0)" onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-[#3B4B3A]">
                Username / Service ID
              </label>
              <div className="relative flex items-center">
                <div className="absolute left-3 text-[#677766] pointer-events-none">
                  <User className="h-4 w-4" />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. demo_commander"
                  required
                  className="w-full pl-9 pr-3.5 py-2.5 bg-white border border-[#CFDDCE] rounded-lg text-xs md:text-sm text-[#182417] placeholder-[#9AA899] focus:outline-none focus:ring-2 focus:ring-[#2C5127] focus:border-[#2C5127] transition-all font-mono"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#3B4B3A]">
                  Secure Credential
                </label>
              </div>
              <div className="relative flex items-center">
                <div className="absolute left-3 text-[#677766] pointer-events-none">
                  <KeyRound className="h-4 w-4" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  className="w-full pl-9 pr-10 py-2.5 bg-white border border-[#CFDDCE] rounded-lg text-xs md:text-sm text-[#182417] placeholder-[#9AA899] focus:outline-none focus:ring-2 focus:ring-[#2C5127] focus:border-[#2C5127] transition-all font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 text-[#677766] hover:text-[#182417] transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3 px-4 bg-[#2C5127] hover:bg-[#1E3A1A] active:bg-[#152B12] text-white font-semibold text-xs md:text-sm tracking-wide rounded-lg transition-all shadow-md shadow-[#2C5127]/20 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <span>AUTHENTICATING SECURE SESSION...</span>
              ) : (
                <>
                  <span>AUTHENTICATE &amp; ENTER</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {/* Privacy Notice */}
          <div className="pt-4 border-t border-[#E4ECE3] flex items-center justify-between text-[11px] text-[#677766]">
            <span className="flex items-center gap-1 font-mono">
              <ShieldCheck className="h-3.5 w-3.5 text-[#15803D]" />
              <span>Argon2id Verification</span>
            </span>
            <span className="font-mono">CAPF Role-Gated Access</span>
          </div>

        </div>
      </div>
    </div>
  );
}
