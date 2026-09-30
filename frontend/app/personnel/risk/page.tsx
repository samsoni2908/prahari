"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PersonnelRiskRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/personnel?tab=risk");
  }, [router]);
  return null;
}
