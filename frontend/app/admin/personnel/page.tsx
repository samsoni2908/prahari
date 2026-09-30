"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AdminPersonnelRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin?tab=personnel");
  }, [router]);
  return null;
}
