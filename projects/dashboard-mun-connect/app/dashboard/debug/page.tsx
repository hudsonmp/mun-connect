"use client"

import { useEffect, useState } from 'react'
import { useAuth } from '../../../lib/auth-context'
import { supabase } from '../../../lib/supabase'
import Link from 'next/link'

export default function DebugPage() {
  const { user, session, refreshSession } = useAuth()
  const [localAuthState, setLocalAuthState] = useState<any>(null)
  const [cookies, setCookies] = useState<Record<string, string>>({})
  const [sessionTest, setSessionTest] = useState<any>(null)
  const [debugOutput, setDebugOutput] = useState<string[]>([])
  
  useEffect(() => {
    // Gather debugging info
    const gatherDebugInfo = async () => {
      // Get localStorage auth state - only runs in browser
      try {
        // Check that we're in a browser environment
        if (typeof window !== 'undefined') {
          // Now safe to use localStorage
          const authState = localStorage.getItem('authState')
          if (authState) {
            setLocalAuthState(JSON.parse(authState))
          }
          
          // Parse cookies
          const cookieObj = document.cookie.split(';').reduce((acc, cookie) => {
            const [key, value] = cookie.trim().split('=')
            if (key) acc[key] = value || 'empty'
            return acc
          }, {} as Record<string, string>)
          setCookies(cookieObj)
          
          // Test session retrieval
          if (supabase) {
            const { data, error } = await supabase.auth.getSession()
            setSessionTest({ 
              hasSession: !!data?.session,
              error: error ? error.message : null,
              timestamp: new Date().toISOString()
            })
            
            addLog('Debug page loaded')
            if (data?.session) {
              addLog(`Session found: ${data.session.user.email}`)
              addLog(`Session expires: ${data.session.expires_at 
                ? new Date(data.session.expires_at * 1000).toLocaleString() 
                : 'No expiry set'}`)
            } else {
              addLog('No active session found')
            }
          } else {
            addLog('Supabase client not initialized')
          }
        }
      } catch (err) {
        console.error('Error gathering debug info:', err)
        addLog(`Error: ${err instanceof Error ? err.message : String(err)}`)
      }
    }
    
    gatherDebugInfo()
  }, [])
  
  const addLog = (message: string) => {
    setDebugOutput(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${message}`])
  }
  
  const handleRefreshSession = async () => {
    addLog('Manually refreshing session...')
    try {
      await refreshSession()
      addLog('Session refresh completed')
      
      // Verify if it worked
      if (typeof window !== 'undefined' && supabase) {
        const { data } = await supabase.auth.getSession()
        if (data?.session) {
          addLog(`Session active for: ${data.session.user.email}`)
        } else {
          addLog('No active session after refresh')
        }
      }
    } catch (err) {
      addLog(`Refresh error: ${err instanceof Error ? err.message : String(err)}`)
    }
  }
  
  const handleClearStorage = () => {
    if (typeof window === 'undefined') return;
    
    addLog('Clearing local storage auth data...')
    localStorage.removeItem('authState')
    localStorage.removeItem('supabase-auth')
    setLocalAuthState(null)
    addLog('Local storage cleared')
  }
  
  const handleForceReauth = async () => {
    if (typeof window === 'undefined' || !supabase) return;
    
    addLog('Forcing reauth - clearing local storage and refreshing session...')
    
    // Clear all auth state
    localStorage.removeItem('authState')
    localStorage.removeItem('supabase-auth')
    setLocalAuthState(null)
    
    try {
      // Sign out first to clear server-side state
      await supabase.auth.signOut()
      addLog('Signed out from Supabase')
      
      // Wait a moment
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // Reload the page to get a clean slate
      addLog('Reloading page to get clean slate...')
      window.location.href = '/dashboard/login'
    } catch (err) {
      addLog(`Reauth error: ${err instanceof Error ? err.message : String(err)}`)
    }
  }
  
  const handleTestApi = async () => {
    if (typeof window === 'undefined' || !supabase) return;
    
    addLog('Testing authenticated API call...')
    try {
      const { data, error } = await supabase.from('profiles').select('*').limit(1)
      
      if (error) {
        addLog(`API error: ${error.message}`)
      } else {
        addLog(`API success: ${data.length} records returned`)
      }
    } catch (err) {
      addLog(`API exception: ${err instanceof Error ? err.message : String(err)}`)
    }
  }
  
  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Authentication Debug Page</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow dark:bg-gray-800">
          <h2 className="text-xl font-semibold mb-4">Auth Context State</h2>
          <div className="space-y-2">
            <p><span className="font-medium">User:</span> {user ? user.email : 'Not logged in'}</p>
            <p><span className="font-medium">Session:</span> {session ? 'Active' : 'None'}</p>
            {session && (
              <>
                <p><span className="font-medium">User ID:</span> {session.user.id}</p>
                <p>
                  <span className="font-medium">Expires:</span> {session.expires_at 
                    ? new Date(session.expires_at * 1000).toLocaleString() 
                    : 'No expiry'}
                </p>
              </>
            )}
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow dark:bg-gray-800">
          <h2 className="text-xl font-semibold mb-4">Local Storage State</h2>
          <div className="space-y-2">
            <p>
              <span className="font-medium">Auth State:</span> {localAuthState 
                ? 'Present' 
                : 'None'}
            </p>
            {localAuthState && (
              <>
                <p>
                  <span className="font-medium">Is Authenticated:</span> {localAuthState.isAuthenticated ? 'Yes' : 'No'}
                </p>
                <p>
                  <span className="font-medium">User ID:</span> {localAuthState.userId}
                </p>
                <p>
                  <span className="font-medium">Last Updated:</span> {new Date(localAuthState.lastUpdated).toLocaleString()}
                </p>
              </>
            )}
            <p>
              <span className="font-medium">Supabase Auth:</span> {typeof window !== 'undefined' && localStorage.getItem('supabase-auth') ? 'Present' : 'Not found'}
            </p>
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow col-span-1 dark:bg-gray-800">
          <h2 className="text-xl font-semibold mb-4">Cookies</h2>
          {Object.keys(cookies).length > 0 ? (
            <ul className="space-y-1 text-sm">
              {Object.entries(cookies).map(([key, value]) => (
                <li key={key}><span className="font-medium">{key}:</span> {value}</li>
              ))}
            </ul>
          ) : (
            <p className="text-red-500">No cookies found</p>
          )}
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow col-span-2 dark:bg-gray-800">
          <h2 className="text-xl font-semibold mb-4">Session Test</h2>
          {sessionTest ? (
            <div className="space-y-2">
              <p>
                <span className="font-medium">Has Session:</span> {sessionTest.hasSession ? 'Yes' : 'No'}
              </p>
              {sessionTest.error && (
                <p className="text-red-500">
                  <span className="font-medium">Error:</span> {sessionTest.error}
                </p>
              )}
              <p>
                <span className="font-medium">Tested at:</span> {new Date(sessionTest.timestamp).toLocaleString()}
              </p>
            </div>
          ) : (
            <p>Testing session...</p>
          )}
        </div>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow mb-8 dark:bg-gray-800">
        <h2 className="text-xl font-semibold mb-4">Debug Log</h2>
        <div className="bg-gray-100 p-4 rounded-md h-48 overflow-y-auto font-mono text-sm dark:bg-gray-900">
          {debugOutput.length > 0 ? (
            debugOutput.map((log, index) => (
              <div key={index} className="whitespace-pre-wrap">{log}</div>
            ))
          ) : (
            <p className="text-gray-500">No logs yet</p>
          )}
        </div>
      </div>
      
      <div className="bg-white p-6 rounded-lg shadow mb-8 dark:bg-gray-800">
        <h2 className="text-xl font-semibold mb-4">Actions</h2>
        <div className="flex flex-wrap gap-4">
          <button 
            onClick={handleRefreshSession}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Refresh Session
          </button>
          <button 
            onClick={handleClearStorage}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Clear Storage
          </button>
          <button 
            onClick={handleForceReauth}
            className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            Force Reauth
          </button>
          <button 
            onClick={handleTestApi}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Test API
          </button>
          <Link 
            href="/dashboard/login" 
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Go to Login
          </Link>
          <Link 
            href="/dashboard" 
            className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
} 