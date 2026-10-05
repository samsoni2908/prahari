"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi, type AuthUser as ApiAuthUser } from "./api";

export interface AuthUser extends ApiAuthUser {
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
      const userData = await authApi.me();
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
      const res = await authApi.login(username, password);
      const authenticatedUser: AuthUser = res.user;

      // Mobile Lockout for Admin: Administrative functions restricted to Web Station
      if (typeof window !== "undefined" && (navigator.userAgent.includes("PrahariMobileApp") || navigator.userAgent.includes("SwastiMobileApp"))) {
        if (authenticatedUser.role === "ADMIN") {
          await authApi.logout();
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
      await authApi.logout();
      setUser(null);
      router.push("/login");
    } finally {
      setIsLoading(false);
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
