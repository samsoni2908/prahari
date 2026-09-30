"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PersonnelDeploymentRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/personnel?tab=deployment");
  }, [router]);
  return null;
}
