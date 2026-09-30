"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth, roleRouteMap } from "@/lib/auth-context";

export default function RootPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading) {
      if (user) {
        const target = roleRouteMap[user.role] || "/login";
        router.replace(target);
      } else {
        router.replace("/login");
      }
    }
  }, [user, isLoading, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-prahari-bg text-prahari-olive">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 rounded-full border-2 border-prahari-oliveBorder animate-ping" />
        <div className="absolute inset-0 rounded-full border-2 border-t-prahari-olive border-r-transparent border-b-prahari-oliveLight border-l-transparent animate-spin" />
      </div>
    </div>
  );
}
