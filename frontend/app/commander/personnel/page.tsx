"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CommanderPersonnelRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/commander?tab=personnel");
  }, [router]);
  return null;
}
