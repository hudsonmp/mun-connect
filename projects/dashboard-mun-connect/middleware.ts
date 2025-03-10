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
]

// Debug flag - set to true to log authentication issues
const DEBUG_AUTH = true

export async function middleware(request: NextRequest) {
  // Check for bypass flag to prevent infinite redirects
  const bypassAuth = request.nextUrl.searchParams.get('bypass_auth') === 'true'
  if (bypassAuth) {
    // Skip all auth checks if bypass is enabled for debugging
    return NextResponse.next()
  }
  
  // Create a response object that we'll use for cookies
  const res = NextResponse.next()
  
  try {
    // Create Supabase client with explicit cookie handling
    const supabase = createMiddlewareClient({ 
      req: request, 
      res,
    })
    
    // Check for auth callback parameters in URL
    const isAuthCallback = request.nextUrl.searchParams.has('access_token') || 
                          request.nextUrl.searchParams.has('refresh_token') ||
                          request.nextUrl.searchParams.has('code')
    
    // If this is an auth callback URL, proceed without redirection
    if (isAuthCallback) {
      if (DEBUG_AUTH) console.log('Auth callback detected, skipping middleware')
      return res
    }
    
    // Check if the pathname matches any auth callback route
    const isAuthCallbackRoute = authCallbackRoutes.some(route => 
      request.nextUrl.pathname.startsWith(route)
    )
    
    // If it's an auth callback route, let it proceed
    if (isAuthCallbackRoute) {
      if (DEBUG_AUTH) console.log('Auth callback route detected, skipping middleware')
      return res
    }
    
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
    // We refresh the session first to ensure it's valid
    const { data: sessionData } = await supabase.auth.getSession()
    const session = sessionData.session
    
    if (DEBUG_AUTH) {
      console.log(`Path: ${request.nextUrl.pathname}`)
      console.log(`Is authenticated: ${!!session}`)
      console.log(`Session expires: ${session?.expires_at ? new Date(session.expires_at * 1000).toISOString() : 'No session'}`)
    }
    
    // Handle auth routes (login, register, etc.)
    if (isAuthRoute) {
      // If authenticated and trying to access auth routes, redirect to dashboard
      if (session) {
        if (DEBUG_AUTH) console.log('User is authenticated, redirecting to dashboard')
        return NextResponse.redirect(new URL('/dashboard', request.url))
      }
      // Otherwise, allow access to auth routes
      return res
    }
    
    // Handle protected routes
    if (isProtectedRoute) {
      // If not authenticated, redirect to login with the current URL as redirect
      if (!session) {
        if (DEBUG_AUTH) console.log('User is not authenticated, redirecting to login')
        
        // Prevent redirect loops by checking for multiple redirects
        if (request.nextUrl.searchParams.has('redirect')) {
          // Already being redirected, add a bypass flag to break potential loops
          const loginUrl = new URL('/dashboard/login', request.url)
          loginUrl.searchParams.set('bypass_auth', 'true')
          return NextResponse.redirect(loginUrl)
        }
        
        const redirectUrl = new URL('/dashboard/login', request.url)
        redirectUrl.searchParams.set('redirect', request.nextUrl.pathname)
        return NextResponse.redirect(redirectUrl)
      }
      
      // Check if profile is complete for routes that require it
      if (session && request.nextUrl.pathname !== '/dashboard/profile-setup') {
        try {
          // Check if user has a username
          const { data: profile, error } = await supabase
            .from('profiles')
            .select('username')
            .eq('id', session.user.id)
            .single()
          
          if (error) {
            if (DEBUG_AUTH) console.log('Error fetching profile:', error)
            // If there's an error fetching the profile, still allow access
            return res
          }
          
          if (!profile?.username) {
            if (DEBUG_AUTH) console.log('Profile incomplete, redirecting to profile setup')
            return NextResponse.redirect(new URL('/dashboard/profile-setup', request.url))
          }
        } catch (error) {
          if (DEBUG_AUTH) console.log('Exception in profile check:', error)
          // If there's an exception, still allow access
          return res
        }
      }
      
      // If authenticated, allow access to protected routes
      return res
    }
  } catch (error) {
    console.error('Middleware error:', error)
    
    // In case of an error, we'll redirect to login but with a bypass flag
    // to prevent an infinite loop if the error persists
    const fallbackUrl = new URL('/dashboard/login', request.url)
    fallbackUrl.searchParams.set('bypass_auth', 'true')
    fallbackUrl.searchParams.set('error', 'auth_error')
    return NextResponse.redirect(fallbackUrl)
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