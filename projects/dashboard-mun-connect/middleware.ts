import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { createServerClient, type CookieOptions } from '@supabase/ssr'

// Base path from next.config
const BASE_PATH = '/dashboard'

// Define protected route patterns - THESE SHOULD NOT INCLUDE THE BASE PATH
const protectedRoutes = [
  '/',
  '/write',
  '/research',
  '/prepare',
  '/conference',
  '/network',
  '/profile',
]

// Define authentication exempt routes - THESE SHOULD NOT INCLUDE THE BASE PATH
const authRoutes = [
  '/login',
  '/register',
  '/profile-setup',
  '/forgot-password',
  '/reset-password',
]

// Paths that should be exempt from redirect loops
const authCallbackRoutes = [
  '/auth/callback',
  '/api/auth',
  '/api/auth/callback',
  '/api', // Basic API routes
]

// Debug flag - enable to log authentication flow details
const DEBUG_AUTH = true

export async function middleware(request: NextRequest) {
  // Create response that we'll modify with cookies if needed
  const res = NextResponse.next()
  
  try {
    // Extract path without base path for cleaner comparison
    const fullPath = request.nextUrl.pathname
    const path = fullPath.startsWith(BASE_PATH) 
      ? fullPath.substring(BASE_PATH.length) || '/'
      : fullPath
    
    // Log the current path for debugging
    if (DEBUG_AUTH) {
      console.log(`Middleware running for path: ${fullPath}`)
      console.log(`Normalized path for comparison: ${path}`)
    }
    
    // CIRCUIT BREAKER: Check for backdoor URL parameter to break infinite redirect loops
    // This is for development/debugging purposes
    if (request.nextUrl.searchParams.has('_auth_bypass')) {
      if (DEBUG_AUTH) console.log('Auth bypass detected, skipping middleware checks')
      return res
    }

    // CALLBACK DETECTION: Always skip middleware for URLs with auth code params
    if (request.nextUrl.searchParams.has('code')) {
      if (DEBUG_AUTH) console.log('Auth code parameter detected, skipping middleware')
      return res
    }
    
    // PATH TYPE DETECTION: Determine what kind of route we're on
    const isAuthCallbackRoute = authCallbackRoutes.some(route => 
      path.startsWith(route)
    )
    
    // Skip middleware for auth callback routes
    if (isAuthCallbackRoute) {
      if (DEBUG_AUTH) console.log('Auth callback route detected, skipping middleware')
      return res
    }
    
    // REDIRECT LOOP DETECTION: Check for too many redirects
    const redirectCount = parseInt(request.cookies.get('redirect_count')?.value || '0')
    if (redirectCount > 3) {
      // Too many redirects, clear cookies and go to login with error
      if (DEBUG_AUTH) console.log('Too many redirects detected, breaking loop')
      const response = NextResponse.redirect(new URL(`${BASE_PATH}/login?error=too_many_redirects`, request.url))
      response.cookies.set('redirect_count', '0')
      return response
    }
    
    // Create Supabase client
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL || '',
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
      {
        cookies: {
          get: (name) => request.cookies.get(name)?.value,
          set: (name, value, options) => {
            res.cookies.set({
              name,
              value,
              ...options,
            });
          },
          remove: (name, options) => {
            res.cookies.set({
              name,
              value: '',
              ...options,
            });
          },
        },
      }
    )
    
    // Check if the path is a protected or auth route (without base path)
    const isProtectedRoute = protectedRoutes.some(route => 
      path === route || 
      (route !== '/' && path.startsWith(route))
    )
    
    const isAuthRoute = authRoutes.some(route => 
      path === route
    )
    
    // Skip middleware for non-protected and non-auth routes
    if (!isProtectedRoute && !isAuthRoute) {
      if (DEBUG_AUTH) console.log(`Non-protected, non-auth route: ${path}, skipping middleware`)
      return res
    }
    
    // SESSION VALIDATION: Get and validate the session
    const { data } = await supabase.auth.getSession()
    const session = data?.session
    
    if (DEBUG_AUTH) {
      console.log(`Path: ${path}`)
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
        // Don't redirect if there's a specific error parameter
        if (request.nextUrl.searchParams.has('error')) {
          if (DEBUG_AUTH) console.log('Error parameter present, allowing access to auth route despite session')
          return res
        }
        
        // User is already logged in, redirect to dashboard
        if (DEBUG_AUTH) console.log('User is authenticated, redirecting from auth route to dashboard')
        const dashboardUrl = new URL(`${BASE_PATH}`, request.url)
        
        // Preserve any redirect parameter
        const redirectParam = request.nextUrl.searchParams.get('redirect')
        if (redirectParam) {
          // Don't add base path again for redirect parameters
          dashboardUrl.pathname = `${BASE_PATH}${redirectParam.startsWith('/') ? redirectParam : '/' + redirectParam}`
        }
        
        return NextResponse.redirect(dashboardUrl)
      }
      // Not logged in, allow access to auth routes
      return res
    }
    
    // PROTECTED ROUTE HANDLING: Routes that require authentication
    if (isProtectedRoute) {
      if (!session) {
        // Not authenticated, redirect to login
        if (DEBUG_AUTH) console.log('User is not authenticated, redirecting to login')
        
        // Get the path for the redirect parameter (WITHOUT base path)
        const redirectPath = path
        
        // Increment redirect counter to detect loops
        const loginRedirect = NextResponse.redirect(
          new URL(`${BASE_PATH}/login?redirect=${encodeURIComponent(redirectPath)}`, request.url)
        )
        loginRedirect.cookies.set('redirect_count', (redirectCount + 1).toString())
        // Ensure cache control headers prevent caching
        loginRedirect.headers.set('Cache-Control', 'no-store, max-age=0')
        return loginRedirect
      }
      
      // User is authenticated, check if profile is complete
      if (path !== '/profile-setup') {
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
            return NextResponse.redirect(new URL(`${BASE_PATH}/profile-setup`, request.url))
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
      // Ensure cache control prevents caching of protected routes
      res.headers.set('Cache-Control', 'no-store, max-age=0')
      return res
    }
  } catch (error) {
    console.error('Middleware exception:', error)
    
    // Emergency fallback to prevent the site from breaking
    const response = NextResponse.redirect(new URL(`${BASE_PATH}/login?error=middleware_error`, request.url))
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
  ],
} 