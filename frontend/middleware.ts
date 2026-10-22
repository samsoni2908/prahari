import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/personnel", "/commander", "/welfare", "/admin", "/dashboard"];

export function middleware(request: NextRequest) {
  // Non-secret UX session presence indicator (Backend RBAC remains authoritative for all data APIs)
  const isLoggedIn = request.cookies.get("prahari_logged_in")?.value === "1";
  const { pathname } = request.nextUrl;

  const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));

  // Protected routes require valid session presence
  if (isProtected) {
    if (!isLoggedIn) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("from", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/personnel/:path*",
    "/commander/:path*",
    "/welfare/:path*",
    "/admin/:path*",
    "/dashboard/:path*",
    "/login"
  ],
};
