"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PersonnelLeaveRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/personnel?tab=leave");
  }, [router]);
  return null;
}
