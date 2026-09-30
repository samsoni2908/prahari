"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CommanderSettingsRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/commander?tab=settings");
  }, [router]);
  return null;
}
