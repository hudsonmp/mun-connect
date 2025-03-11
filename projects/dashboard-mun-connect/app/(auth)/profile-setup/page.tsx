"use client"

import React, { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useAuth } from "../../../lib/auth-context"
import { supabase } from "../../../lib/supabase"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../../components/ui/select"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../../components/ui/card"
import { CheckCircle, ChevronRight, Loader2 } from "lucide-react"

const formSchema = z.object({
  username: z.string().min(3, { message: "Username must be at least 3 characters" }),
  fullName: z.string().optional(),
  bio: z.string().max(160, { message: "Bio must be less than 160 characters" }).optional(),
  country: z.string().optional(),
  interests: z.array(z.string()).optional(),
})

const INTERESTS = [
  "International Relations",
  "Diplomacy",
  "Public Speaking",
  "Debate",
  "Current Affairs",
  "Environmental Policy",
  "Human Rights",
  "Economic Development",
  "Security",
  "Technology Policy",
]

const COUNTRIES = [
  "United States",
  "United Kingdom",
  "Canada",
  "Australia",
  "Germany",
  "France",
  "Japan",
  "China",
  "India",
  "Brazil",
  "South Africa",
  "Other",
]

export default function ProfileSetupPage() {
  const { user, session } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  const [step, setStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedInterests, setSelectedInterests] = useState<string[]>([])

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      username: "",
      fullName: "",
      bio: "",
      country: "",
      interests: [],
    },
  })

  const handleInterestToggle = (interest: string) => {
    setSelectedInterests(prev => 
      prev.includes(interest)
        ? prev.filter(i => i !== interest)
        : [...prev, interest]
    )
    
    form.setValue("interests", 
      selectedInterests.includes(interest)
        ? selectedInterests.filter(i => i !== interest)
        : [...selectedInterests, interest]
    )
  }

  const nextStep = () => {
    if (step === 1) {
      const usernameValue = form.getValues("username")
      if (!usernameValue || usernameValue.length < 3) {
        form.setError("username", { 
          type: "manual", 
          message: "Username is required and must be at least 3 characters" 
        })
        return
      }
    }
    setStep(prev => prev + 1)
  }

  const prevStep = () => {
    setStep(prev => prev - 1)
  }

  async function onSubmit(values: z.infer<typeof formSchema>) {
    if (!user) {
      toast({
        variant: "destructive",
        title: "Not authenticated",
        description: "Please sign in to complete your profile.",
      })
      router.push("/login")
      return
    }

    setIsLoading(true)
    try {
      // Update with selected interests
      values.interests = selectedInterests

      if (!supabase) {
        throw new Error("Supabase client is not initialized")
      }

      const { error } = await supabase
        .from('profiles')
        .upsert({
          id: user.id,
          username: values.username,
          full_name: values.fullName || null,
          bio: values.bio || null,
          country: values.country || null,
          interests: values.interests || [],
          conference_experience: [],
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
      
      if (error) {
        toast({
          variant: "destructive",
          title: "Profile setup failed",
          description: error.message || "Please try again.",
        })
        return
      }
      
      toast({
        title: "Profile created",
        description: "Your profile has been set up successfully!",
      })
      
      router.push("/dashboard")
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

  if (!user) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Authentication Required</CardTitle>
            <CardDescription>
              Please sign in to set up your profile.
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Button onClick={() => router.push("/login")} className="w-full">
              Go to Login
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Set Up Your Profile</CardTitle>
          <CardDescription>
            {step === 1 && "Let's start with the basics"}
            {step === 2 && "Tell us a bit about yourself"}
            {step === 3 && "What are you interested in?"}
          </CardDescription>
          <div className="flex justify-between mt-4">
            <div className="flex space-x-2">
              <div className={`h-2 w-2 rounded-full ${step >= 1 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
              <div className={`h-2 w-2 rounded-full ${step >= 2 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
              <div className={`h-2 w-2 rounded-full ${step >= 3 ? 'bg-blue-600' : 'bg-gray-300'}`}></div>
            </div>
            <div className="text-sm text-gray-500">Step {step} of 3</div>
          </div>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              {step === 1 && (
                <>
                  <FormField
                    control={form.control}
                    name="username"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Username*</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="your_username" 
                            {...field} 
                            className="bg-gray-50 dark:bg-gray-800"
                          />
                        </FormControl>
                        <FormDescription>
                          This will be your unique identifier on MUN Connect
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="fullName"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Full Name (Optional)</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="Jane Doe" 
                            {...field} 
                            className="bg-gray-50 dark:bg-gray-800"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </>
              )}

              {step === 2 && (
                <>
                  <FormField
                    control={form.control}
                    name="bio"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Bio (Optional)</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder="Tell us a bit about yourself..." 
                            {...field} 
                            className="bg-gray-50 dark:bg-gray-800 min-h-[100px]"
                          />
                        </FormControl>
                        <FormDescription>
                          Max 160 characters
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="country"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Country (Optional)</FormLabel>
                        <Select 
                          onValueChange={field.onChange} 
                          defaultValue={field.value}
                        >
                          <FormControl>
                            <SelectTrigger className="bg-gray-50 dark:bg-gray-800">
                              <SelectValue placeholder="Select your country" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {COUNTRIES.map((country) => (
                              <SelectItem key={country} value={country}>
                                {country}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </>
              )}

              {step === 3 && (
                <FormField
                  control={form.control}
                  name="interests"
                  render={() => (
                    <FormItem>
                      <FormLabel>Interests (Optional)</FormLabel>
                      <FormDescription>
                        Select topics you&apos;re interested in
                      </FormDescription>
                      <div className="grid grid-cols-2 gap-2 mt-3">
                        {INTERESTS.map((interest) => (
                          <Button
                            key={interest}
                            type="button"
                            variant={selectedInterests.includes(interest) ? "default" : "outline"}
                            className={`justify-start h-auto py-2 px-3 text-left ${
                              selectedInterests.includes(interest) 
                                ? "bg-blue-600 text-white" 
                                : "bg-gray-50 dark:bg-gray-800"
                            }`}
                            onClick={() => handleInterestToggle(interest)}
                          >
                            {selectedInterests.includes(interest) && (
                              <CheckCircle className="mr-2 h-4 w-4" />
                            )}
                            <span className="truncate">{interest}</span>
                          </Button>
                        ))}
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}
            </form>
          </Form>
        </CardContent>
        <CardFooter className="flex justify-between">
          {step > 1 ? (
            <Button 
              variant="outline" 
              onClick={prevStep}
              className="bg-gray-50 dark:bg-gray-800"
            >
              Back
            </Button>
          ) : (
            <div></div>
          )}
          
          {step < 3 ? (
            <Button onClick={nextStep}>
              Continue <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <Button 
              onClick={form.handleSubmit(onSubmit)}
              disabled={isLoading}
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Complete Setup"
              )}
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  )
} 