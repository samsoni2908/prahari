"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CommanderUnitOverviewRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/commander?tab=unit_overview");
  }, [router]);
  return null;
}
