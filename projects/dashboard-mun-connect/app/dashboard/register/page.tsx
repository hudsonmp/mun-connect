"use client"

import React from "react"
import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useAuth } from "../../../lib/auth-context"
import { Button } from "../../../components/ui/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "../../../components/ui/form"
import { Input } from "../../../components/ui/input"
import { Textarea } from "../../../components/ui/textarea"
import { useToast } from "../../../components/ui/use-toast"
import { Loader2, Upload } from "lucide-react"
import { DashboardHeader } from "../../../components/dashboard/dashboard-header"
import { Avatar, AvatarFallback, AvatarImage } from "../../../components/ui/avatar"
import { supabase } from "../../../lib/supabase"

const formSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address" }),
  password: z.string().min(6, { message: "Password must be at least 6 characters" }),
  confirmPassword: z.string().min(6, { message: "Password must be at least 6 characters" }),
  username: z.string().min(3, { message: "Username must be at least 3 characters" }),
  fullName: z.string().optional(),
  bio: z.string().max(250, { message: "Bio cannot exceed 250 characters" }).optional(),
  avatarUrl: z.string().optional(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
})

export default function RegisterPage() {
  const { signUp } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  const [isLoading, setIsLoading] = useState(false)
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)
  const [showEmailConfirmation, setShowEmailConfirmation] = useState(false)

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
      username: "",
      fullName: "",
      bio: "",
      avatarUrl: "",
    },
  })

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null
    
    if (file) {
      setAvatarFile(file)
      const reader = new FileReader()
      reader.onload = (e) => {
        setAvatarPreview(e.target?.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const uploadAvatar = async (userId: string): Promise<string | null> => {
    if (!avatarFile) return null
    
    try {
      // Create a unique file path
      const fileExt = avatarFile.name.split('.').pop()
      const filePath = `avatars/${userId}/${Date.now()}.${fileExt}`
      
      // Upload to Supabase Storage
      const { error } = await supabase.storage
        .from('profiles')
        .upload(filePath, avatarFile)
      
      if (error) throw error
      
      // Get the public URL
      const { data } = supabase.storage.from('profiles').getPublicUrl(filePath)
      return data.publicUrl
    } catch (error) {
      console.error('Error uploading avatar:', error)
      return null
    }
  }

  async function onSubmit(values: z.infer<typeof formSchema>) {
    setIsLoading(true)
    try {
      // Step 1: Register the user
      const { error, data } = await signUp(values.email, values.password)
      
      if (error) {
        toast({
          variant: "destructive",
          title: "Registration failed",
          description: error.message || "Please check your information and try again.",
        })
        setIsLoading(false)
        return
      }
      
      // Step 2: If successful, upload avatar and update profile
      if (data?.user) {
        const userId = data.user.id
        
        // Upload avatar if provided
        const avatarUrl = await uploadAvatar(userId)
        
        // Update the user's profile in the profiles table
        const { error: profileError } = await supabase
          .from('profiles')
          .upsert({
            id: userId,
            username: values.username,
            full_name: values.fullName || null,
            bio: values.bio || null,
            avatar_url: avatarUrl,
            updated_at: new Date().toISOString(),
          })
        
        if (profileError) {
          toast({
            variant: "destructive",
            title: "Profile update failed",
            description: "Your account was created but we couldn't save your profile details.",
          })
          setIsLoading(false)
          
          // Even if profile update fails, check if email confirmation is needed
          if (data.user.email_confirmed_at) {
            router.push('/dashboard/login')
          } else {
            // Show confirmation email alert
            setShowEmailConfirmation(true)
          }
          return
        }
        
        toast({
          title: "Registration successful",
          description: data.user.email_confirmed_at 
            ? "Your account has been created successfully! You can now log in."
            : "Your account has been created. Please check your email to confirm your registration.",
        })
        
        // Check if email confirmation is needed
        if (data.user.email_confirmed_at) {
          // Already confirmed, redirect to login
          router.push('/dashboard/login')
        } else {
          // Show confirmation email alert
          setShowEmailConfirmation(true)
        }
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Something went wrong",
        description: "Please try again later.",
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <DashboardHeader />
      <div className="flex min-h-[calc(100vh-64px)] flex-col items-center justify-center bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 p-4">
        {showEmailConfirmation ? (
          <div className="w-full max-w-lg space-y-8 bg-white dark:bg-gray-900 p-8 rounded-xl shadow-lg">
            <div className="text-center">
              <h1 className="text-3xl font-bold tracking-tight text-blue-600 dark:text-blue-400">
                Check your email
              </h1>
              <p className="mt-4 text-gray-600 dark:text-gray-400">
                We've sent a confirmation email to <span className="font-medium">{form.getValues().email}</span>.
              </p>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Please click the link in the email to verify your account.
              </p>
              
              <div className="mt-8 p-4 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  <strong>Note:</strong> After confirming your email, you'll be redirected to the dashboard. If you're not automatically redirected, please return to the login page.
                </p>
              </div>
              
              <div className="mt-8">
                <Button 
                  onClick={() => router.push('/dashboard/login')}
                  className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                >
                  Return to login
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-lg space-y-8 bg-white dark:bg-gray-900 p-8 rounded-xl shadow-lg">
            <div className="text-center">
              <h1 className="text-3xl font-bold tracking-tight text-blue-600 dark:text-blue-400">
                Create your account
              </h1>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Join MUN Connect to access all features
              </p>
            </div>

            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                {/* Avatar Upload */}
                <div className="flex flex-col items-center space-y-4">
                  <Avatar className="h-24 w-24 border-2 border-blue-200 dark:border-blue-800">
                    {avatarPreview ? (
                      <AvatarImage src={avatarPreview} alt="Preview" />
                    ) : (
                      <AvatarFallback className="text-lg">
                        <Upload className="h-8 w-8 text-gray-400" />
                      </AvatarFallback>
                    )}
                  </Avatar>
                  
                  <div>
                    <label 
                      htmlFor="avatar-upload" 
                      className="cursor-pointer text-sm text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      Upload profile picture
                    </label>
                    <input
                      id="avatar-upload"
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleFileChange}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Email Field */}
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
                  
                  {/* Username Field */}
                  <FormField
                    control={form.control}
                    name="username"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Username</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="username" 
                            {...field} 
                            className="bg-gray-50 dark:bg-gray-800"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                
                {/* Full Name Field */}
                <FormField
                  control={form.control}
                  name="fullName"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Full Name (Optional)</FormLabel>
                      <FormControl>
                        <Input 
                          placeholder="John Doe" 
                          {...field} 
                          className="bg-gray-50 dark:bg-gray-800"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                {/* Bio Field */}
                <FormField
                  control={form.control}
                  name="bio"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Bio (Optional)</FormLabel>
                      <FormControl>
                        <Textarea 
                          placeholder="Tell us a bit about yourself" 
                          {...field} 
                          className="bg-gray-50 dark:bg-gray-800 resize-none"
                        />
                      </FormControl>
                      <FormDescription>
                        Max 250 characters
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Password Field */}
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
                  
                  {/* Confirm Password Field */}
                  <FormField
                    control={form.control}
                    name="confirmPassword"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Confirm Password</FormLabel>
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
                </div>
                
                <Button 
                  type="submit" 
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Creating account...
                    </>
                  ) : (
                    "Create account"
                  )}
                </Button>
              </form>
            </Form>

            <div className="mt-6 text-center text-sm">
              <p className="text-gray-600 dark:text-gray-400">
                Already have an account?{" "}
                <Link 
                  href="/dashboard/login" 
                  className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
                >
                  Sign in
                </Link>
              </p>
            </div>
          </div>
        )}
      </div>
    </>
  )
} 