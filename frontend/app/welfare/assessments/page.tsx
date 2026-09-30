"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function WelfareAssessmentsRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/welfare?tab=assessments");
  }, [router]);
  return null;
}
