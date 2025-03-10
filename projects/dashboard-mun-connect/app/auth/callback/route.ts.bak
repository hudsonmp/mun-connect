import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  // Get the URL and its parameters
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const next = requestUrl.searchParams.get('next') || '/dashboard'
  
  if (code) {
    // Create a Supabase client
    const cookieStore = cookies()
    const supabase = createRouteHandlerClient({ cookies: () => cookieStore })
    
    // Exchange the code for a session
    await supabase.auth.exchangeCodeForSession(code)
    
    // Clear any URL fragments that might have been added
    if (requestUrl.hash) {
      requestUrl.hash = ''
    }
    
    // Redirect to the dashboard or specified page
    return NextResponse.redirect(new URL(next, requestUrl.origin))
  }
  
  // If there's no code, redirect to the login page
  return NextResponse.redirect(new URL('/dashboard/login', requestUrl.origin))
} 