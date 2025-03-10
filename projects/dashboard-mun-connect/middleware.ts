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

// Paths that should be exempt from redirect loops
const authCallbackRoutes = [
  '/auth/callback',
  '/api/auth',
  '/auth/confirm',
  '/dashboard/auth/callback',
]

// Debug flag - enable to log authentication flow details
const DEBUG_AUTH = true

export async function middleware(request: NextRequest) {
  // Create response that we'll modify with cookies if needed
  const res = NextResponse.next()
  
  try {
    // CIRCUIT BREAKER: Check for backdoor URL parameter to break infinite redirect loops
    // This is for development/debugging purposes
    if (request.nextUrl.searchParams.has('_auth_bypass')) {
      if (DEBUG_AUTH) console.log('Auth bypass detected, skipping middleware checks')
      return res
    }
    
    // REDIRECT LOOP DETECTION: Check for too many redirects
    const redirectCount = parseInt(request.cookies.get('redirect_count')?.value || '0')
    if (redirectCount > 3) {
      // Too many redirects, clear cookies and go to login with error
      if (DEBUG_AUTH) console.log('Too many redirects detected, breaking loop')
      const response = NextResponse.redirect(new URL('/dashboard/login?error=too_many_redirects', request.url))
      response.cookies.set('redirect_count', '0')
      return response
    }
    
    // Create Supabase client
    const supabase = createMiddlewareClient({ req: request, res })
    
    // PATH TYPE DETECTION: Determine what kind of route we're on
    const isAuthCallbackRoute = authCallbackRoutes.some(route => 
      request.nextUrl.pathname.startsWith(route)
    )
    
    // Skip middleware for auth callback routes
    if (isAuthCallbackRoute || request.nextUrl.searchParams.has('code')) {
      if (DEBUG_AUTH) console.log('Auth callback route detected, skipping middleware')
      return res
    }
    
    const isProtectedRoute = protectedRoutes.some(route => 
      request.nextUrl.pathname.startsWith(route)
    )
    
    const isAuthRoute = authRoutes.some(route => 
      request.nextUrl.pathname.startsWith(route)
    )
    
    // Skip middleware for non-protected and non-auth routes
    if (!isProtectedRoute && !isAuthRoute) {
      return res
    }
    
    // SESSION VALIDATION: Get and validate the session
    const { data } = await supabase.auth.getSession()
    const session = data?.session
    
    if (DEBUG_AUTH) {
      console.log(`Path: ${request.nextUrl.pathname}`)
      console.log(`Is authenticated: ${!!session}`)
      if (session) {
        const expiresAt = session.expires_at ? new Date(session.expires_at * 1000) : 'No expiry'
        console.log(`Session expires: ${expiresAt}`)
        console.log(`User ID: ${session.user.id}`)
      }
    }
    
    // AUTH ROUTE HANDLING: Routes like login, register, etc.
    if (isAuthRoute) {
      if (session) {
        // User is already logged in, redirect to dashboard
        if (DEBUG_AUTH) console.log('User is authenticated, redirecting from auth route to dashboard')
        return NextResponse.redirect(new URL('/dashboard', request.url))
      }
      // Not logged in, allow access to auth routes
      return res
    }
    
    // PROTECTED ROUTE HANDLING: Routes that require authentication
    if (isProtectedRoute) {
      if (!session) {
        // Not authenticated, redirect to login
        if (DEBUG_AUTH) console.log('User is not authenticated, redirecting to login')
        
        // Increment redirect counter to detect loops
        const loginRedirect = NextResponse.redirect(
          new URL(`/dashboard/login?redirect=${encodeURIComponent(request.nextUrl.pathname)}`, request.url)
        )
        loginRedirect.cookies.set('redirect_count', (redirectCount + 1).toString())
        return loginRedirect
      }
      
      // User is authenticated, check if profile is complete
      if (request.nextUrl.pathname !== '/dashboard/profile-setup') {
        try {
          const { data: profile, error } = await supabase
            .from('profiles')
            .select('username')
            .eq('id', session.user.id)
            .single()
          
          if (error) {
            if (DEBUG_AUTH) console.log('Error fetching profile:', error)
            // Error fetching profile, still allow access to avoid redirect loops
            return res
          }
          
          if (!profile?.username) {
            if (DEBUG_AUTH) console.log('Profile incomplete, redirecting to profile setup')
            return NextResponse.redirect(new URL('/dashboard/profile-setup', request.url))
          }
        } catch (error) {
          console.error('Exception checking profile:', error)
          // Exception occurred, still allow access
          return res
        }
      }
      
      // Authentication and profile checks passed, allow access
      if (DEBUG_AUTH) console.log('Auth checks passed, allowing access to protected route')
      
      // Reset redirect count since we're not redirecting
      res.cookies.set('redirect_count', '0')
      return res
    }
  } catch (error) {
    console.error('Middleware exception:', error)
    
    // Emergency fallback to prevent the site from breaking
    const response = NextResponse.redirect(new URL('/dashboard/login?error=middleware_error', request.url))
    response.cookies.set('redirect_count', '0') // Reset redirect count
    return response
  }
  
  return res
}

// Configure middleware to match specific paths
export const config = {
  matcher: [
    '/dashboard',
    '/dashboard/:path*',
    '/auth/:path*',
    '/api/auth/:path*',
  ],
} 