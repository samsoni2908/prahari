"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AdminSystemRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin?tab=system");
  }, [router]);
  return null;
}
