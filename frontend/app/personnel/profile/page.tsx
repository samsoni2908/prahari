"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PersonnelProfileRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/personnel?tab=profile");
  }, [router]);
  return null;
}
