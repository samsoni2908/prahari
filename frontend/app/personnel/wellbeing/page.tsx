"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PersonnelWellbeingRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/personnel?tab=wellbeing");
  }, [router]);
  return null;
}
