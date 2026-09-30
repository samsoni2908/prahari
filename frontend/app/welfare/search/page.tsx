"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function WelfareSearchRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/welfare?tab=search");
  }, [router]);
  return null;
}
