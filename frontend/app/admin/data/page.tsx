"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AdminDataRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin?tab=data_management");
  }, [router]);
  return null;
}
