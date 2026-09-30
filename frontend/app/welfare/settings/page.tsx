"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function WelfareSettingsRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/welfare?tab=settings");
  }, [router]);
  return null;
}
