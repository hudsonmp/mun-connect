"use client"

import { useState, useEffect, Suspense } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useAuth } from "@/lib/auth-context"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { useToast } from "@/components/ui/use-toast"
import { Loader2 } from "lucide-react"

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
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)

  // If already authenticated, redirect to the specified path
  useEffect(() => {
    if (!isLoading && user) {
      router.push(redirectPath)
    }
  }, [user, isLoading, router, redirectPath])

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  })

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsSubmitting(true)
    try {
      const { error } = await signIn(values.email, values.password)
      
      if (error) {
        toast({
          variant: "destructive",
          title: "Login failed",
          description: error.message || "Please check your credentials and try again.",
        })
        return
      }
      
      toast({
        title: "Login successful",
        description: "Welcome back to MUN Connect!",
      })
      
      // Redirect to the specified path or dashboard
      router.push(redirectPath)
    } catch (error) {
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
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 p-4">
      <div className="w-full max-w-md space-y-8 bg-white dark:bg-gray-900 p-8 rounded-xl shadow-lg">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-blue-600 dark:text-blue-400">
            Welcome back
          </h1>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Sign in to your MUN Connect account
          </p>
        </div>

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
              {isSubmitting ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </Form>

        <div className="mt-6 text-center text-sm">
          <p className="text-gray-600 dark:text-gray-400">
            Don't have an account?{" "}
            <Link 
              href="/register" 
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
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 p-4">
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
    <Suspense fallback={<LoginLoading />}>
      <LoginForm />
    </Suspense>
  )
} 