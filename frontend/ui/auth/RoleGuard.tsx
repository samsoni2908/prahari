"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth, roleRouteMap } from "@/lib/auth-context";
import { ShieldAlert, ArrowLeft } from "lucide-react";

interface RoleGuardProps {
  allowedRoles: Array<"PERSONNEL" | "COMMANDER" | "WELFARE_OFFICER" | "ADMIN">;
  children: React.ReactNode;
}

export const RoleGuard: React.FC<RoleGuardProps> = ({ allowedRoles, children }) => {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-prahari-bg text-prahari-olive">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-2 border-emerald-500/20 animate-ping" />
          <div className="absolute inset-0 rounded-full border-2 border-t-emerald-700 border-r-transparent border-b-emerald-600/30 border-l-transparent animate-spin" />
        </div>
        <p className="mt-4 font-mono text-sm tracking-widest text-[#728070] uppercase">
          SECURE CHANNEL VERIFICATION...
        </p>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  if (!allowedRoles.includes(user.role)) {
    const authorizedPortal = roleRouteMap[user.role] || "/login";

    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-prahari-bg text-prahari-textPrimary">
        <div className="max-w-md w-full bg-white p-8 rounded-xl border border-red-200 text-center shadow-lg">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-50 border border-red-200 flex items-center justify-center text-red-600">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold tracking-wider text-red-700 font-mono">
            403 — ACCESS RESTRICTED
          </h2>
          <p className="mt-2 text-sm text-[#465444]">
            Your credentials ({user.role}) are not authorized to access this compartment under PRAHARI RBAC rules.
          </p>
          <div className="mt-6 pt-4 border-t border-gray-100 flex justify-center">
            <button
              onClick={() => router.push(authorizedPortal)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#EFF5EE] border border-[#CDE0CB] hover:bg-[#E2ECE0] text-[#243D20] text-sm font-semibold transition-all"
            >
              <ArrowLeft className="w-4 h-4" />
              Return to Authorized Portal ({user.role})
            </button>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
