"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { authApi, clearStoredSession, setStoredSession, type AuthUser as ApiAuthUser } from "./api";

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
      setStoredSession();
      setUser(userData);
    } catch {
      clearStoredSession();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  useEffect(() => {
    const onExpired = () => {
      setUser(null);
      setIsLoading(false);
      router.replace("/login");
    };
    window.addEventListener("prahari:session-expired", onExpired);
    return () => window.removeEventListener("prahari:session-expired", onExpired);
  }, [router]);

  const login = async (username: string, password: string): Promise<AuthUser> => {
    setIsLoading(true);
    try {
      const res = await authApi.login(username, password);
      const authenticatedUser: AuthUser = res.user;

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
