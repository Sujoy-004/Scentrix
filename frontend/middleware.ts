import { NextRequest, NextResponse } from 'next/server';

// Define public routes that don't require authentication
const publicRoutes = [
  '/',
  '/auth/login',
  '/auth/register',
  '/auth/forgot-password',
  '/fragrances',
  '/families',
  '/recommendations',
  '/terms',
  '/privacy',
];

// Define routes that require authentication
const protectedRoutes = [
  '/profile',
  '/user',
];


export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  
  // Check if the request is for a static asset, API route, or static file
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.startsWith('/public') ||
    pathname.match(/\.(js|css|png|jpg|jpeg|gif|svg|ico|webp|woff|woff2)$/)
  ) {
    return NextResponse.next();
  }

  // Try to get auth token from cookie (set by login API)
  const authToken = request.cookies.get('auth_token')?.value;
  const isPublicRoute = publicRoutes.some((route) => pathname === route || pathname.startsWith(route + '/'));
  const isProtectedRoute = protectedRoutes.some((route) => pathname.startsWith(route));

  // If trying to access a protected route without auth, redirect to login
  if (isProtectedRoute && !authToken) {
    const loginUrl = new URL('/auth/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // If authenticated and trying to access auth pages, redirect to recommendations
  if ((pathname === '/auth/login' || pathname === '/auth/register') && authToken) {
    return NextResponse.redirect(new URL('/recommendations', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!api|_next/static|_next/image|favicon.ico|public|__next).*)',
  ],
};
