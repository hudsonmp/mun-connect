import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'

// Define protected route patterns
const protectedRoutes = [
  '/dashboard',
  '/dashboard/write',
  '/dashboard/research',
  '/dashboard/prepare',
  '/dashboard/conference',
  '/dashboard/network',
  '/dashboard/profile',
]

// Define authentication exempt routes
const authRoutes = [
  '/dashboard/login',
  '/dashboard/register',
  '/dashboard/profile-setup',
  '/dashboard/forgot-password',
  '/dashboard/reset-password',
]

export async function middleware(request: NextRequest) {
  const res = NextResponse.next()
  const supabase = createMiddlewareClient({ req: request, res })
  
  // Check if the pathname matches any protected route pattern
  const isProtectedRoute = protectedRoutes.some(route => 
    request.nextUrl.pathname.startsWith(route)
  )
  
  // Check if the pathname is an auth route
  const isAuthRoute = authRoutes.some(route => 
    request.nextUrl.pathname.startsWith(route)
  )
  
  // We don't need to check non-protected and non-auth routes
  if (!isProtectedRoute && !isAuthRoute) {
    return res
  }
  
  // Get the session - check if user is authenticated
  const { data: { session } } = await supabase.auth.getSession()
  
  // Handle auth routes (login, register, etc.)
  if (isAuthRoute) {
    // If authenticated and trying to access auth routes, redirect to dashboard
    if (session) {
      return NextResponse.redirect(new URL('/dashboard', request.url))
    }
    // Otherwise, allow access to auth routes
    return res
  }
  
  // Handle protected routes
  if (isProtectedRoute) {
    // If not authenticated, redirect to login with the current URL as redirect
    if (!session) {
      const redirectUrl = new URL('/dashboard/login', request.url)
      redirectUrl.searchParams.set('redirect', request.nextUrl.pathname)
      return NextResponse.redirect(redirectUrl)
    }
    
    // Check if profile is complete for routes that require it
    if (session && request.nextUrl.pathname !== '/dashboard/profile-setup') {
      // Check if user has a username
      const { data: profile } = await supabase
        .from('profiles')
        .select('username')
        .eq('id', session.user.id)
        .single()
      
      if (!profile?.username) {
        return NextResponse.redirect(new URL('/dashboard/profile-setup', request.url))
      }
    }
    
    // If authenticated, allow access to protected routes
    return res
  }
  
  return res
}

// Configure middleware to match specific paths
export const config = {
  matcher: [
    '/dashboard',
    '/dashboard/:path*',
  ],
} 