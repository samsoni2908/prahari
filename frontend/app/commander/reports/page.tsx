"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CommanderReportsRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/commander?tab=reports");
  }, [router]);
  return null;
}
