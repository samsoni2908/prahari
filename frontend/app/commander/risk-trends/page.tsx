"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CommanderRiskTrendsRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/commander?tab=risk_trends");
  }, [router]);
  return null;
}
