"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function WelfareRiskMonitorRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/welfare?tab=risk_monitor");
  }, [router]);
  return null;
}
