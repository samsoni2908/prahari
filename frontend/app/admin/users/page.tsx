"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function AdminUsersRoute() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/admin?tab=users");
  }, [router]);
  return null;
}
