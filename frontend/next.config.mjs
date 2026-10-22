/** @type {import('next').NextConfig} */
const BACKEND_INTERNAL_URL =
  process.env.BACKEND_INTERNAL_URL ||
  (process.env.NODE_ENV === "production" ? "http://backend:8000" : "http://localhost:8000");

const isDev = process.env.NODE_ENV !== "production";

// Development CSP: allows 'unsafe-eval' required by Next.js React Refresh/HMR.
// Without 'unsafe-eval', the dev runtime JS fails silently, React never hydrates,
// and form submissions fall through as native browser GET requests (produces /login?).
// Production CSP remains strict — no unsafe-eval.
const devCSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "img-src 'self' data: blob:",
  "font-src 'self' data: https://fonts.gstatic.com",
  "connect-src 'self' ws://localhost:3000 ws://127.0.0.1:3000 http://localhost:3000 http://127.0.0.1:3000",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const prodCSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "img-src 'self' data: blob:",
  "font-src 'self' data: https://fonts.gstatic.com",
  "connect-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_INTERNAL_URL}/api/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Content-Security-Policy",
            value: isDev ? devCSP : prodCSP,
          },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
