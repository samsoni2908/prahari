"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AdminSettingsRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin?tab=settings");
  }, [router]);
  return null;
}
