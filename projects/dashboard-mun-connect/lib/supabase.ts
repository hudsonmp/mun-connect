"use client"

import { createClient } from '@supabase/supabase-js'
import type { Database } from './database.types'
// Remove the auth-helpers-nextjs import as it's outdated and causing conflicts
// import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { createBrowserClient } from '@supabase/ssr'

// Debug flag for auth issues
const DEBUG_AUTH = true

// Get environment variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
const redirectUrl = process.env.NEXT_PUBLIC_REDIRECT_URL || '/dashboard/auth/callback'

// Validate environment variables
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Missing Supabase environment variables.')
  if (DEBUG_AUTH) {
    console.log('NEXT_PUBLIC_SUPABASE_URL:', supabaseUrl || 'undefined')
    console.log('NEXT_PUBLIC_SUPABASE_ANON_KEY:', supabaseAnonKey ? '[REDACTED]' : 'undefined')
    console.log('Environment:', process.env.NODE_ENV)
  }
}

// Custom fetch implementation to work around Next.js caching issues
const customFetch = async (url: RequestInfo | URL, options?: RequestInit) => {
  try {
    // Add a cache-busting parameter to avoid Next.js caching
    const urlObj = new URL(url.toString());
    urlObj.searchParams.append('_t', Date.now().toString());
    
    // Use the global fetch with the modified URL
    const response = await fetch(urlObj.toString(), {
      ...options,
      // Ensure we're not using Next.js cache
      cache: 'no-store',
      next: { revalidate: 0 }
    });
    
    return response;
  } catch (error) {
    console.error('Supabase fetch error:', error);
    throw error;
  }
};

// Helper function to use MCP for data access when available
export const mcpQuery = async (query: string, params?: any[]) => {
  try {
    if (typeof window === 'undefined') {
      // For server-side, use direct PostgreSQL connection
      // This is handled by the backend
      return null;
    }
    
    // Use MCP client if it's available
    // @ts-ignore - MCP global is injected by Cursor
    if (typeof window !== 'undefined' && window.mcp && window.mcp.query) {
      // @ts-ignore
      const result = await window.mcp.query(query, params);
      console.log('MCP query executed successfully:', query.substring(0, 50) + (query.length > 50 ? '...' : ''));
      return result;
    }
    
    // If MCP isn't available, try to use our custom MCP server
    const mcpUrl = process.env.NEXT_PUBLIC_MCP_URL || 'http://localhost:8765';
    try {
      const response = await fetch(`${mcpUrl}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, params: params || [] }),
        // Ensure we're not using Next.js cache
        cache: 'no-store',
        next: { revalidate: 0 }
      });
      
      if (!response.ok) {
        throw new Error(`MCP server responded with status: ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Custom MCP server query executed successfully');
      return result;
    } catch (mcpServerError) {
      console.warn('Custom MCP server error:', mcpServerError);
      console.warn('Falling back to Supabase API');
    }
    
    console.warn('MCP not available, SQL queries will be executed via Supabase API');
    return null;
  } catch (error) {
    console.error('MCP query error:', error);
    return null;
  }
};

// SINGLETON PATTERN: Create a single Supabase client instance
// This prevents multiple GoTrueClient instances
let supabaseInstance: ReturnType<typeof createBrowserClient<Database>> | null = null;

export const getSupabase = () => {
  if (typeof window === 'undefined') {
    // Server-side - create a new instance each time
    // This is safe as it won't persist between requests
    return createClient<Database>(
      supabaseUrl || '',
      supabaseAnonKey || '',
      {
        auth: {
          flowType: 'pkce',
          autoRefreshToken: true,
          persistSession: false,
          detectSessionInUrl: false,
        },
        global: {
          fetch: customFetch
        }
      }
    );
  }

  // Client-side - use singleton pattern
  if (!supabaseInstance) {
    console.log('Creating new Supabase client instance');
    supabaseInstance = createBrowserClient<Database>(
      supabaseUrl || '',
      supabaseAnonKey || '',
      {
        cookies: {
          get(name: string) {
            return document.cookie
              .split('; ')
              .find(row => row.startsWith(`${name}=`))
              ?.split('=')[1];
          },
          set(name: string, value: string, options: any) {
            document.cookie = `${name}=${value}; ${Object.entries(options)
              .map(([key, val]) => `${key}=${val}`)
              .join('; ')}`;
          },
          remove(name: string, options: any) {
            document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; ${Object.entries(options)
              .map(([key, val]) => `${key}=${val}`)
              .join('; ')}`;
          }
        },
        auth: {
          flowType: 'pkce',
          autoRefreshToken: true,
          persistSession: true,
          detectSessionInUrl: true,
          storageKey: 'supabase.auth.token',
          storage: typeof window !== 'undefined' ? window.localStorage : undefined
        },
        global: {
          fetch: customFetch
        }
      }
    );
  }

  return supabaseInstance;
};

// Export a consistent singleton instance
export const supabase = typeof window !== 'undefined' ? getSupabase() : null;

// Initialize session and set up error recovery
if (typeof window !== 'undefined') {
  console.log('Initializing Supabase client...')
  
  // Set up session initialization and error handling
  const initializeSession = async () => {
    try {
      if (DEBUG_AUTH) console.log('Initializing Supabase client and session')
      
      // First check if we have a stored auth state that claims we're authenticated
      let storedAuthState = null;
      let localAuthClaim = false;
      let localUserId = null;
      
      try {
        storedAuthState = localStorage.getItem('authState');
      } catch (error) {
        console.error('Error accessing localStorage:', error);
      }
      
      if (storedAuthState) {
        try {
          const authState = JSON.parse(storedAuthState);
          localUserId = authState.userId;
          const lastUpdated = new Date(authState.lastUpdated);
          const now = new Date();
          const hoursSinceUpdate = (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60);
          
          // If auth state is recent and claims authentication
          if (hoursSinceUpdate < 24 && authState.isAuthenticated && authState.userId) {
            localAuthClaim = true;
            if (DEBUG_AUTH) console.log('Found recent local auth state claiming authentication for user:', authState.userId);
            
            // Update some metadata in the stored auth state
            const updatedAuthState = {
              ...authState,
              lastUpdated: new Date().toISOString(),
              currentUrl: window.location.href,
              userAgent: navigator.userAgent,
              hasSupabaseAuth: false // Will update this later if we find a session
            };
            
            try {
              localStorage.setItem('authState', JSON.stringify(updatedAuthState));
            } catch (error) {
              console.error('Error updating authState in localStorage:', error);
            }
          }
        } catch (e) {
          console.error('Error parsing auth state:', e);
          // Clear corrupted auth state
          try {
            localStorage.removeItem('authState');
          } catch (error) {
            console.error('Error removing authState from localStorage:', error);
          }
        }
      }
      
      if (!supabase) {
        console.error('Supabase client not initialized');
        return;
      }
      
      // Try to get current session
      const { data, error } = await supabase.auth.getSession()
      
      if (error) {
        console.error('Error initializing session:', error)
        
        // If we have a local auth claim but Supabase session failed, try to restore it
        if (localAuthClaim && localUserId && supabase) {
          if (DEBUG_AUTH) console.log('Attempting to recover session based on local auth claim');
          try {
            const refreshResult = await supabase.auth.refreshSession();
            if (refreshResult.data?.session) {
              if (DEBUG_AUTH) console.log('Successfully refreshed session from local auth claim');
              // Update auth state to indicate we have a Supabase session
              try {
                const currentAuthState = JSON.parse(localStorage.getItem('authState') || '{}');
                localStorage.setItem('authState', JSON.stringify({
                  ...currentAuthState,
                  hasSupabaseAuth: true,
                  lastUpdated: new Date().toISOString()
                }));
              } catch (error) {
                console.error('Error updating auth state after session refresh:', error);
              }
            }
          } catch (refreshError) {
            console.error('Failed to refresh session:', refreshError);
          }
        }
        
        return
      }
      
      if (data?.session && supabase) {
        if (DEBUG_AUTH) {
          console.log('Session initialized successfully')
          const expiresAt = data.session.expires_at 
            ? new Date(data.session.expires_at * 1000) 
            : 'No expiry'
          console.log(`Session expires at: ${expiresAt}`)
          console.log(`User ID: ${data.session.user.id}`)
        }
        
        // Ensure the session is properly set in Supabase
        try {
          await supabase.auth.setSession({
            access_token: data.session.access_token,
            refresh_token: data.session.refresh_token,
          })
          if (DEBUG_AUTH) console.log('Session explicitly set')
          
          // Ensure localStorage is synced with this valid session
          try {
            localStorage.setItem('authState', JSON.stringify({
              isAuthenticated: true,
              userId: data.session.user.id,
              hasSupabaseAuth: true,
              lastUpdated: new Date().toISOString(),
              currentUrl: window.location.href,
              userAgent: navigator.userAgent
            }));
          } catch (error) {
            console.error('Error syncing auth state to localStorage:', error);
          }
        } catch (err) {
          console.error('Error setting session:', err)
        }
      } else {
        if (DEBUG_AUTH) console.log('No active session found during initialization')
        
        // If Supabase has no session but we have a local auth claim, 
        // try one more time to refresh the session
        if (localAuthClaim && localUserId && supabase) {
          if (DEBUG_AUTH) console.log('Auth state mismatch: Local claims auth but Supabase has no session. Attempting final refresh.');
          try {
            const refreshResult = await supabase.auth.refreshSession();
            if (refreshResult.data?.session) {
              if (DEBUG_AUTH) console.log('Successfully refreshed session in final attempt');
              
              // Update auth state to indicate we have a Supabase session
              try {
                localStorage.setItem('authState', JSON.stringify({
                  isAuthenticated: true,
                  userId: refreshResult.data.session.user.id,
                  hasSupabaseAuth: true,
                  lastUpdated: new Date().toISOString(),
                  currentUrl: window.location.href,
                  userAgent: navigator.userAgent
                }));
              } catch (error) {
                console.error('Error updating auth state after final refresh:', error);
              }
              
              return;
            } else {
              // If refresh failed, clear the auth state
              if (DEBUG_AUTH) console.log('Failed to refresh session in final attempt, clearing local storage');
              try {
                localStorage.removeItem('authState');
                localStorage.removeItem('supabase-auth');
              } catch (error) {
                console.error('Error clearing auth state after failed refresh:', error);
              }
              
              // Force reload to ensure clean state
              if (!window.location.pathname.includes('/login')) {
                if (DEBUG_AUTH) console.log('Redirecting to login after auth failure');
                window.location.href = '/dashboard/login';
              }
            }
          } catch (refreshError) {
            console.error('Failed in final refresh attempt:', refreshError);
            try {
              localStorage.removeItem('authState');
              localStorage.removeItem('supabase-auth');
            } catch (error) {
              console.error('Error clearing auth state after refresh error:', error);
            }
          }
        }
      }
    } catch (err) {
      console.error('Exception initializing session:', err)
    }
  }
  
  // Run the initialization
  initializeSession()
  
  // Store the redirect URL for reference in other components
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('supabaseRedirectUrl', redirectUrl)
      if (DEBUG_AUTH) console.log('Redirect URL stored:', redirectUrl)
    }
  } catch (error) {
    console.error('Error storing redirect URL:', error);
  }
  
  // Listen for auth state changes
  if (supabase) {
    supabase.auth.onAuthStateChange((event, session) => {
      if (DEBUG_AUTH) console.log('Auth state changed in Supabase client:', event)
      
      if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
        if (DEBUG_AUTH) console.log('User signed in or token refreshed')
        
        // Update backup auth state
        if (session) {
          try {
            localStorage.setItem('authState', JSON.stringify({
              isAuthenticated: true,
              userId: session.user.id,
              hasSupabaseAuth: true,
              lastUpdated: new Date().toISOString(),
              currentUrl: window.location.href,
              userAgent: navigator.userAgent
            }));
          } catch (error) {
            console.error('Error updating auth state on sign in:', error);
          }
        }
      } else if (event === 'SIGNED_OUT') {
        if (DEBUG_AUTH) console.log('User signed out')
        try {
          localStorage.removeItem('authState');
          localStorage.removeItem('supabase-auth');
        } catch (error) {
          console.error('Error clearing auth state on sign out:', error);
        }
      }
    })
  
    // Set up error handling for storage events
    window.addEventListener('storage', (event) => {
      if (event.key === 'supabase-auth' && event.newValue !== event.oldValue) {
        if (DEBUG_AUTH) console.log('Storage event: auth state changed externally')
        
        // Refresh the page to sync auth state
        window.location.reload()
      }
    })
  
    // Add a recovery mechanism for stuck auth initialization
    setTimeout(() => {
      try {
        const authStateRaw = localStorage.getItem('authState');
        if (authStateRaw) {
          try {
            const authState = JSON.parse(authStateRaw);
            if (authState.isAuthenticated && !authState.hasSupabaseAuth) {
              if (DEBUG_AUTH) console.log('Detected stuck auth initialization after timeout');
              // Try to refresh the session
              supabase.auth.refreshSession().then(({ data, error }) => {
                if (error) {
                  if (DEBUG_AUTH) console.log('Failed to refresh session after timeout:', error);
                  if (!window.location.pathname.includes('/login')) {
                    window.location.href = '/dashboard/login';
                  }
                } else if (data.session) {
                  if (DEBUG_AUTH) console.log('Successfully refreshed session after timeout');
                  try {
                    localStorage.setItem('authState', JSON.stringify({
                      ...authState,
                      hasSupabaseAuth: true,
                      lastUpdated: new Date().toISOString()
                    }));
                  } catch (error) {
                    console.error('Error updating auth state after timeout refresh:', error);
                  }
                  // Reload the page to ensure all components reflect the correct auth state
                  window.location.reload();
                }
              });
            }
          } catch (e) {
            console.error('Error parsing auth state during recovery:', e);
          }
        }
      } catch (error) {
        console.error('Error accessing localStorage during recovery:', error);
      }
    }, 5000); // Check after 5 seconds
  }
}

// Export the database type
export type { Database } 