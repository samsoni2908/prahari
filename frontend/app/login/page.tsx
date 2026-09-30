"use client";

import React, { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { Shield, Eye, EyeOff, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState<string>("personnel");
  const [password, setPassword] = useState<string>("prahari123");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      setError("Please enter your Service Number/Email and Password.");
      return;
    }
    setIsSubmitting(true);
    try {
      await login(username.trim(), password);
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please verify your credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-prahari-bg">
      {/* Top Hero — Defence Olive Green Banner */}
      <div
        className="flex-shrink-0 px-6 pt-16 pb-12 text-white flex flex-col items-center"
        style={{
          background: "linear-gradient(160deg, #243D20 0%, #2E4F28 50%, #385E31 100%)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.12)",
        }}
      >
        {/* Shield + Logo */}
        <div
          className="mb-4 w-20 h-20 rounded-2xl flex items-center justify-center shadow-lg"
          style={{ background: "rgba(255,255,255,0.18)", border: "1.5px solid rgba(255,255,255,0.28)" }}
        >
          <Shield className="w-10 h-10 text-white" />
        </div>

        <h1 className="text-4xl font-extrabold tracking-widest text-white">
          SWASTI
        </h1>
        <p className="text-sm font-semibold text-emerald-100/90 mt-1 text-center tracking-wide">
          People &nbsp;•&nbsp; Wellness &nbsp;•&nbsp; Readiness
        </p>
        <p className="text-xs text-emerald-100/75 mt-2 text-center max-w-xs leading-relaxed">
          AI-Powered Personnel Stress and Welfare Monitoring System
        </p>
      </div>

      {/* White card — form */}
      <div className="flex-1 bg-prahari-bg flex items-start justify-center px-4 -mt-6 pb-12">
        <div
          className="w-full max-w-sm bg-white rounded-2xl p-7 animate-slide-up border border-[#E1E8DF]"
          style={{ boxShadow: "0 8px 32px rgba(28, 40, 26, 0.08)" }}
        >
          <h2 className="text-xl font-bold text-prahari-textPrimary mb-1">Welcome Back</h2>
          <p className="text-sm text-prahari-textMuted mb-6">Sign in to your SWASTI secure account</p>

          {/* Error */}
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-prahari-highBg border border-prahari-highBorder flex items-start gap-2.5 text-sm text-prahari-high">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label htmlFor="username" className="form-label">
                Service Number / Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <svg className="w-4 h-4 text-prahari-textMuted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. personnel / commander"
                  disabled={isSubmitting}
                  className="form-input pl-10"
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="form-label">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <svg className="w-4 h-4 text-prahari-textMuted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  disabled={isSubmitting}
                  className="form-input pl-10 pr-10"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-prahari-textMuted hover:text-prahari-textSecondary transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember me */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  defaultChecked
                  className="w-4 h-4 rounded border-gray-300 text-[#385E31] focus:ring-[#385E31]"
                />
                <span className="text-sm text-prahari-textSecondary">Remember me</span>
              </label>
              <span className="text-xs text-prahari-textMuted" title="Contact Unit Administrator for password reset">
                Forgot password?
              </span>
            </div>

            <button
              type="submit"
              id="login-submit-btn"
              disabled={isSubmitting}
              className="btn-primary w-full justify-center py-3 text-base mt-2"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Signing In...
                </span>
              ) : (
                "Sign In"
              )}
            </button>
          </form>

          {/* Quick Demo Credentials */}
          <div className="mt-6 pt-4 border-t border-[#E1E8DF]">
            <p className="text-[11px] font-semibold text-prahari-textMuted uppercase tracking-wider mb-2 text-center">
              Quick Role Switch
            </p>
            <div className="grid grid-cols-2 gap-1.5 text-xs">
              {[
                { role: "Personnel", u: "personnel" },
                { role: "Commander", u: "commander" },
                { role: "Welfare", u: "welfare" },
                { role: "Admin", u: "admin" },
              ].map((c) => (
                <button
                  key={c.u}
                  type="button"
                  onClick={() => { setUsername(c.u); setPassword("prahari123"); }}
                  className="px-2 py-1.5 rounded-lg bg-[#EFF5EE] hover:bg-[#E2ECE0] text-[#243D20] text-center font-medium transition-colors border border-[#CDE0CB]"
                >
                  {c.role}
                </button>
              ))}
            </div>
          </div>

          <p className="mt-4 text-center text-xs text-prahari-textMuted">
            Defence Intranet Session • RBAC Enforcement Active
          </p>
        </div>
      </div>
    </div>
  );
}
