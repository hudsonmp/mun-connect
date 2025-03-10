"use client"

import React, { useState, useEffect, Suspense } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useAuth } from "../../../lib/auth-context"
import { supabase } from "../../../lib/supabase"
import { Button } from "../../../components/ui/button"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "../../../components/ui/form"
import { Input } from "../../../components/ui/input"
import { useToast } from "../../../components/ui/use-toast"
import { Loader2, AlertCircle } from "lucide-react"
import { DashboardHeader } from "../../../components/dashboard/dashboard-header"

// Debug flag
const DEBUG_AUTH = true

const formSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address" }),
  password: z.string().min(6, { message: "Password must be at least 6 characters" }),
})

// Component that uses searchParams
function LoginForm() {
  const { signIn, user, isLoading } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const redirectPath = searchParams.get('redirect') || '/dashboard'
  const authError = searchParams.get('error')
  const errorDescription = searchParams.get('error_description')
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [loginAttempts, setLoginAttempts] = useState(0)
  const [authErrorState, setAuthErrorState] = useState<string | null>(null)

  // If already authenticated, redirect to the specified path
  useEffect(() => {
    if (!isLoading && user) {
      if (DEBUG_AUTH) console.log("User authenticated, redirecting to:", redirectPath)
      
      // Use window.location for a full page reload to ensure session is picked up
      window.location.href = redirectPath
    }
  }, [user, isLoading, redirectPath])

  // Show error message if there's an auth error in URL
  useEffect(() => {
    if (authError) {
      let errorMessage = errorDescription || "Authentication error occurred. Please try again."
      
      if (authError === 'session_error') {
        errorMessage = "There was a problem with your session. Please try logging in again."
      } else if (authError === 'callback_exception') {
        errorMessage = "An unexpected error occurred during authentication. Please try again later."
      } else if (authError === 'too_many_redirects') {
        errorMessage = "Too many redirects occurred. This could be due to cookie issues."
      } else if (authError === 'middleware_error') {
        errorMessage = "An error occurred in the authentication middleware."
      }
      
      setAuthErrorState(errorMessage)
      
      toast({
        variant: "destructive",
        title: "Authentication Error",
        description: errorMessage,
      })
    }
  }, [authError, errorDescription, toast])

  // Check localStorage for existing auth state
  useEffect(() => {
    if (!user && !isLoading) {
      const storedAuthState = localStorage.getItem('authState')
      if (storedAuthState) {
        try {
          const authState = JSON.parse(storedAuthState)
          const lastUpdated = new Date(authState.lastUpdated)
          const now = new Date()
          const hoursSinceUpdate = (now.getTime() - lastUpdated.getTime()) / (1000 * 60 * 60)
          
          // If auth state is less than 24 hours old, try to restore the session
          if (hoursSinceUpdate < 24 && authState.isAuthenticated) {
            if (DEBUG_AUTH) console.log("Found recent auth state, attempting to restore session")
            
            // Try to get an active session
            supabase.auth.getSession().then(({ data, error }) => {
              if (!error && data.session) {
                if (DEBUG_AUTH) console.log("Session restored successfully")
                
                // Set session explicitly
                supabase.auth.setSession({
                  access_token: data.session.access_token,
                  refresh_token: data.session.refresh_token,
                }).then(() => {
                  // Use window.location for full page reload
                  window.location.href = redirectPath
                })
              } else {
                if (DEBUG_AUTH) console.log("Could not restore session:", error)
                localStorage.removeItem('authState')
              }
            })
          } else {
            // Auth state is too old
            localStorage.removeItem('authState')
          }
        } catch (e) {
          console.error("Error parsing auth state:", e)
          localStorage.removeItem('authState')
        }
      }
    }
  }, [isLoading, user, redirectPath])

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  })

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsSubmitting(true)
    setLoginAttempts(prev => prev + 1)
    setAuthErrorState(null)
    
    try {
      if (DEBUG_AUTH) console.log("Attempting to sign in user:", values.email)
      const { error, data } = await signIn(values.email, values.password)
      
      if (error) {
        if (DEBUG_AUTH) console.error("Sign in error:", error)
        
        const errorMessage = error.message || "Please check your credentials and try again."
        setAuthErrorState(errorMessage)
        
        toast({
          variant: "destructive",
          title: "Login failed",
          description: errorMessage,
        })
        
        // If we've tried multiple times, suggest password reset
        if (loginAttempts >= 2) {
          toast({
            title: "Trouble logging in?",
            description: (
              <div>
                <p>You can <Link href="/dashboard/forgot-password" className="underline text-blue-600">reset your password</Link> if needed.</p>
              </div>
            ),
          })
        }
        
        return
      }
      
      if (data?.session) {
        if (DEBUG_AUTH) console.log("Login successful, redirecting to:", redirectPath)
        
        toast({
          title: "Login successful",
          description: "Welcome back to MUN Connect!",
        })
        
        // Force reload the page to ensure session is picked up
        window.location.href = redirectPath
      } else {
        if (DEBUG_AUTH) console.log("No session returned after login")
        
        setAuthErrorState("Logged in but no session was created. Please try again.")
        
        toast({
          variant: "destructive",
          title: "Login issue",
          description: "Logged in but no session was created. Please try again.",
        })
      }
    } catch (error) {
      console.error("Exception during login:", error)
      setAuthErrorState("An unexpected error occurred. Please try again later.")
      
      toast({
        variant: "destructive",
        title: "Something went wrong",
        description: "Please try again later.",
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-64px)] flex-col items-center justify-center bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 p-4">
      <div className="w-full max-w-md space-y-8 bg-white dark:bg-gray-900 p-8 rounded-xl shadow-lg">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-blue-600 dark:text-blue-400">
            Welcome back
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Sign in to your MUN Connect account
          </p>
        </div>

        {authErrorState && (
          <div className="p-4 mb-4 bg-red-50 dark:bg-red-900/20 rounded-md border border-red-200 dark:border-red-800">
            <div className="flex items-start">
              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 mr-2" />
              <div>
                <p className="text-sm font-medium text-red-800 dark:text-red-300">
                  Authentication error
                </p>
                <p className="mt-1 text-sm text-red-700 dark:text-red-400">
                  {authErrorState}
                </p>
              </div>
            </div>
          </div>
        )}

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="you@example.com" 
                      type="email" 
                      {...field} 
                      className="bg-gray-50 dark:bg-gray-800"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Password</FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="••••••••" 
                      type="password" 
                      {...field} 
                      className="bg-gray-50 dark:bg-gray-800"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button 
              type="submit" 
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                "Sign in"
              )}
            </Button>
            
            <div className="flex items-center justify-between text-sm">
              <Link 
                href="/dashboard/forgot-password" 
                className="text-blue-600 hover:underline dark:text-blue-400"
              >
                Forgot password?
              </Link>
              
              <button 
                type="button"
                onClick={() => window.location.href = redirectPath + '?_auth_bypass=true'}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 text-xs"
              >
                Bypass Auth (Debug)
              </button>
            </div>
          </form>
        </Form>

        <div className="mt-6 text-center text-sm">
          <p className="text-gray-600 dark:text-gray-400">
            Don&apos;t have an account?{" "}
            <Link 
              href="/dashboard/register" 
              className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
            >
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}

// Loading fallback
function LoginLoading() {
  return (
    <div className="flex min-h-[calc(100vh-64px)] flex-col items-center justify-center bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 p-4">
      <div className="flex flex-col items-center">
        <Loader2 className="h-12 w-12 animate-spin text-blue-600 mb-4" />
        <p className="text-blue-600 font-medium">Loading...</p>
      </div>
    </div>
  )
}

// Main page component with Suspense
export default function LoginPage() {
  return (
    <>
      <DashboardHeader />
      <Suspense fallback={<LoginLoading />}>
        <LoginForm />
      </Suspense>
    </>
  )
} 