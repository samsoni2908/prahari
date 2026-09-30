"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function WelfareReportsRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/welfare?tab=reports");
  }, [router]);
  return null;
}
