"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PersonnelSettingsRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/personnel?tab=settings");
  }, [router]);
  return null;
}
