import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import AppShell from "@/components/layout/AppShell";
import { AuthProvider } from "@/lib/auth-context";

export const metadata: Metadata = {
  title: "PRAHARI — Operational Workload and Welfare Support",
  description: "Privacy-preserving operational workload and recovery decision support for uniformed services.",
  manifest: "/manifest.json",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="theme-color" content="#2C5127" />
      </head>
      <body>
        <AuthProvider>
          <Suspense fallback={<div className="min-h-screen bg-[#FBFBF8]" aria-label="Loading application" />}>
            <AppShell>{children}</AppShell>
          </Suspense>
        </AuthProvider>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  var isDev = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
                  if (isDev) {
                    // In development: unregister all stale service workers first.
                    // Stale workers can intercept navigation/auth requests and cause /login? reload bug.
                    navigator.serviceWorker.getRegistrations().then(function(regs) {
                      regs.forEach(function(reg) { reg.unregister(); });
                    });
                  } else {
                    // Production: register updated service worker.
                    navigator.serviceWorker.register('/sw.js?v=2').catch(function(err) {
                      console.warn('SW registration failed:', err);
                    });
                  }
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
