"use client";

import { useEffect } from "react";
import { useRouter, useParams } from "next/navigation";

export default function WelfarePersonnelDossierRoute() {
  const router = useRouter();
  const params = useParams();

  useEffect(() => {
    const id = params?.id as string;
    if (id) {
      router.replace(`/welfare?tab=personnel&personnel_id=${id}`);
    } else {
      router.replace("/welfare?tab=personnel");
    }
  }, [router, params]);

  return null;
}
