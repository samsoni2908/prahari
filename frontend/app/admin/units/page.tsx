"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AdminUnitsRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin?tab=units");
  }, [router]);
  return null;
}
