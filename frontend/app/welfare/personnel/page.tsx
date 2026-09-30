"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function WelfarePersonnelRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/welfare?tab=personnel");
  }, [router]);
  return null;
}
