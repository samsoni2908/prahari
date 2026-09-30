import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED_PREFIXES = ["/personnel", "/commander", "/welfare", "/admin", "/dashboard"];

export function middleware(request: NextRequest) {
  const sessionCookie = request.cookies.get("prahari_session");
  const { pathname } = request.nextUrl;

  const isProtected = PROTECTED_PREFIXES.some((prefix) => pathname.startsWith(prefix));

  // Protected routes require valid session cookie
  if (isProtected) {
    if (!sessionCookie || !sessionCookie.value) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("from", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // If authenticated and visiting login page, redirect to root which routes to role dashboard
  if (pathname === "/login") {
    if (sessionCookie && sessionCookie.value) {
      return NextResponse.redirect(new URL("/", request.url));
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
