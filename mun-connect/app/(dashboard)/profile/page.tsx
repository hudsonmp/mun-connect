"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { useAuth } from "@/lib/auth-context"
import { supabase } from "@/lib/supabase"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/components/ui/use-toast"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { CheckCircle, Loader2, User } from "lucide-react"

const formSchema = z.object({
  username: z.string().min(3, { message: "Username must be at least 3 characters" }),
  fullName: z.string().optional(),
  bio: z.string().max(160, { message: "Bio must be less than 160 characters" }).optional(),
  country: z.string().optional(),
  interests: z.array(z.string()).optional(),
  conferenceExperience: z.array(z.string()).optional(),
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

export default function ProfilePage() {
  const { user } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  const [isLoading, setIsLoading] = useState(false)
  const [isFetching, setIsFetching] = useState(true)
  const [selectedInterests, setSelectedInterests] = useState<string[]>([])
  const [conferenceExperience, setConferenceExperience] = useState<string[]>([])
  const [newConference, setNewConference] = useState("")

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      username: "",
      fullName: "",
      bio: "",
      country: "",
      interests: [],
      conferenceExperience: [],
    },
  })

  useEffect(() => {
    async function fetchProfile() {
      if (!user) return
      
      try {
        const { data, error } = await supabase
          .from('profiles')
          .select('*')
          .eq('id', user.id)
          .single()
        
        if (error) {
          console.error('Error fetching profile:', error)
          return
        }
        
        if (data) {
          form.reset({
            username: data.username || "",
            fullName: data.full_name || "",
            bio: data.bio || "",
            country: data.country || "",
            interests: data.interests || [],
            conferenceExperience: data.conference_experience || [],
          })
          
          setSelectedInterests(data.interests || [])
          setConferenceExperience(data.conference_experience || [])
        }
      } catch (error) {
        console.error('Error:', error)
      } finally {
        setIsFetching(false)
      }
    }
    
    fetchProfile()
  }, [user, form])

  const handleInterestToggle = (interest: string) => {
    setSelectedInterests(prev => 
      prev.includes(interest)
        ? prev.filter(i => i !== interest)
        : [...prev, interest]
    )
  }

  const addConference = () => {
    if (newConference.trim() && !conferenceExperience.includes(newConference.trim())) {
      const updatedExperience = [...conferenceExperience, newConference.trim()]
      setConferenceExperience(updatedExperience)
      setNewConference("")
    }
  }

  const removeConference = (conference: string) => {
    setConferenceExperience(prev => prev.filter(c => c !== conference))
  }

  async function onSubmit(values: z.infer<typeof formSchema>) {
    if (!user) {
      toast({
        variant: "destructive",
        title: "Not authenticated",
        description: "Please sign in to update your profile.",
      })
      router.push("/login")
      return
    }

    setIsLoading(true)
    try {
      const { error } = await supabase
        .from('profiles')
        .upsert({
          id: user.id,
          username: values.username,
          full_name: values.fullName || null,
          bio: values.bio || null,
          country: values.country || null,
          interests: selectedInterests,
          conference_experience: conferenceExperience,
          updated_at: new Date().toISOString(),
        })
      
      if (error) {
        toast({
          variant: "destructive",
          title: "Profile update failed",
          description: error.message || "Please try again.",
        })
        return
      }
      
      toast({
        title: "Profile updated",
        description: "Your profile has been updated successfully!",
      })
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
      <div className="container mx-auto py-10">
        <Card>
          <CardHeader>
            <CardTitle>Authentication Required</CardTitle>
            <CardDescription>
              Please sign in to view your profile.
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Button onClick={() => router.push("/login")}>
              Go to Login
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  if (isFetching) {
    return (
      <div className="container mx-auto py-10 flex justify-center items-center min-h-[60vh]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-10">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1">
          <Card>
            <CardHeader>
              <div className="flex flex-col items-center">
                <Avatar className="h-24 w-24 mb-4">
                  <AvatarImage src="/placeholder.svg?height=96&width=96" alt={form.getValues("username")} />
                  <AvatarFallback className="text-lg">
                    {form.getValues("username").substring(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <CardTitle>{form.getValues("fullName") || form.getValues("username")}</CardTitle>
                <CardDescription className="mt-1">@{form.getValues("username")}</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {form.getValues("bio") && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">Bio</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{form.getValues("bio")}</p>
                  </div>
                )}
                
                {form.getValues("country") && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">Country</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{form.getValues("country")}</p>
                  </div>
                )}
                
                {selectedInterests.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">Interests</h4>
                    <div className="flex flex-wrap gap-1">
                      {selectedInterests.map(interest => (
                        <span 
                          key={interest} 
                          className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                        >
                          {interest}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {conferenceExperience.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">Conference Experience</h4>
                    <ul className="space-y-1">
                      {conferenceExperience.map(conference => (
                        <li key={conference} className="text-sm text-gray-600 dark:text-gray-400">
                          • {conference}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
        
        <div className="md:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Edit Profile</CardTitle>
              <CardDescription>
                Update your profile information
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
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
                          />
                        </FormControl>
                        <FormDescription>
                          Your unique identifier on MUN Connect
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
                        <FormLabel>Full Name</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="Jane Doe" 
                            {...field} 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={form.control}
                    name="bio"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Bio</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder="Tell us a bit about yourself..." 
                            {...field} 
                            className="min-h-[100px]"
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
                        <FormLabel>Country</FormLabel>
                        <Select 
                          onValueChange={field.onChange} 
                          defaultValue={field.value}
                          value={field.value}
                        >
                          <FormControl>
                            <SelectTrigger>
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
                  
                  <div className="space-y-3">
                    <FormLabel>Interests</FormLabel>
                    <FormDescription>
                      Select topics you're interested in
                    </FormDescription>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {INTERESTS.map((interest) => (
                        <Button
                          key={interest}
                          type="button"
                          variant={selectedInterests.includes(interest) ? "default" : "outline"}
                          className={`justify-start h-auto py-2 px-3 text-left ${
                            selectedInterests.includes(interest) 
                              ? "bg-blue-600 text-white" 
                              : ""
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
                  </div>
                  
                  <div className="space-y-3">
                    <FormLabel>Conference Experience</FormLabel>
                    <FormDescription>
                      Add conferences you've attended
                    </FormDescription>
                    
                    <div className="flex gap-2">
                      <Input 
                        placeholder="e.g., HMUN 2023" 
                        value={newConference}
                        onChange={(e) => setNewConference(e.target.value)}
                      />
                      <Button 
                        type="button" 
                        onClick={addConference}
                        variant="outline"
                      >
                        Add
                      </Button>
                    </div>
                    
                    {conferenceExperience.length > 0 && (
                      <div className="space-y-2 mt-3">
                        {conferenceExperience.map(conference => (
                          <div key={conference} className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-800 rounded-md">
                            <span>{conference}</span>
                            <Button 
                              type="button" 
                              variant="ghost" 
                              size="sm"
                              onClick={() => removeConference(conference)}
                              className="h-8 w-8 p-0 text-red-500"
                            >
                              &times;
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  
                  <Button 
                    type="submit" 
                    className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      "Save Changes"
                    )}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
} 