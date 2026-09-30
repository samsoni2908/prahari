"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CommanderWorkloadRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/commander?tab=workload");
  }, [router]);
  return null;
}
