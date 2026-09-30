"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CommanderLeaveRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/commander?tab=leave");
  }, [router]);
  return null;
}
