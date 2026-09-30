"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "./api";

export interface AuthUser {
  id: string;
  username: string;
  role: "PERSONNEL" | "COMMANDER" | "WELFARE_OFFICER" | "ADMIN";
  personnel_id?: string | null;
  unit_id?: string | null;
  full_name?: string | null;
  unit_code?: string | null;
}

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const roleRouteMap: Record<AuthUser["role"], string> = {
  PERSONNEL: "/personnel",
  COMMANDER: "/commander",
  WELFARE_OFFICER: "/welfare",
  ADMIN: "/admin",
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  const refreshUser = async () => {
    try {
      const userData = await api.get<AuthUser>("/auth/me");
      setUser(userData);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (username: string, password: string): Promise<AuthUser> => {
    setIsLoading(true);
    try {
      const res = await api.post("/auth/login", { username, password });
      const authenticatedUser: AuthUser = res.user;

      // Mobile Lockout for Admin: Administrative functions restricted to Web Station
      if (typeof window !== "undefined" && (navigator.userAgent.includes("PrahariMobileApp") || navigator.userAgent.includes("SwastiMobileApp"))) {
        if (authenticatedUser.role === "ADMIN") {
          await api.post("/auth/logout").catch(() => {});
          setUser(null);
          setIsLoading(false);
          throw new Error("Access Denied: Administrative functions require the SWASTI Secure Web Console. Mobile access is restricted to Personnel, Commander, and Welfare roles.");
        }
      }

      setUser(authenticatedUser);
      setIsLoading(false);

      // Route to designated role portal
      const targetRoute = roleRouteMap[authenticatedUser.role] || "/login";
      router.push(targetRoute);
      return authenticatedUser;
    } catch (err) {
      setIsLoading(false);
      throw err;
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await api.post("/auth/logout");
    } catch {
      // ignore logout network errors
    } finally {
      setUser(null);
      setIsLoading(false);
      router.push("/login");
    }
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
