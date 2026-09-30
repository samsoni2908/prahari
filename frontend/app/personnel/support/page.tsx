"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PersonnelSupportRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/personnel?tab=support");
  }, [router]);
  return null;
}
