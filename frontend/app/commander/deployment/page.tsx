"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CommanderDeploymentRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/commander?tab=deployment");
  }, [router]);
  return null;
}
