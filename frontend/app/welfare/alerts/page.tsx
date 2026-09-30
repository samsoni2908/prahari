"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function WelfareAlertsRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/welfare?tab=alerts");
  }, [router]);
  return null;
}
