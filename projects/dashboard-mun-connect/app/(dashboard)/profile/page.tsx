"use client"

import React, { useState, useEffect } from "react"
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
import { Avatar, AvatarFallback, AvatarImage } from "../../../components/ui/avatar"
import { CheckCircle, Upload, Loader2, User, Building2, GraduationCap, MapPin } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../../components/ui/tabs"

const formSchema = z.object({
  username: z.string()
    .min(3, { message: "Username must be at least 3 characters" })
    .max(50, { message: "Username must be less than 50 characters" })
    .regex(/^[a-zA-Z0-9_-]+$/, { message: "Username can only contain letters, numbers, underscores and hyphens" }),
  fullName: z.string().max(100).optional(),
  bio: z.string().max(300, { message: "Bio must be less than 300 characters" }).optional(),
  country: z.string().optional(),
  school: z.string().max(100).optional(),
  educationLevel: z.enum(["middle_school", "high_school", "university", "other"]).optional(),
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

const EDUCATION_LEVELS = [
  { id: "middle_school", name: "Middle School" },
  { id: "high_school", name: "High School" },
  { id: "university", name: "University" },
  { id: "other", name: "Other" },
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
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const isVercel = typeof window !== 'undefined' && 
    (window.location.hostname.includes('vercel.app') || 
     process.env.NEXT_PUBLIC_VERCEL_ENV === 'production');

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      username: "",
      fullName: "",
      bio: "",
      country: "",
      school: "",
      educationLevel: undefined,
      interests: [],
      conferenceExperience: [],
    },
  })

  useEffect(() => {
    if (isVercel) {
      console.log("Running on Vercel deployment");
    } else {
      console.log("Running in local development");
    }
  }, [isVercel]);

  useEffect(() => {
    async function fetchProfile() {
      if (!user || !supabase) return
      
      try {
        console.log("Fetching profile data for user:", user.id)
        console.log("Using Supabase URL:", process.env.NEXT_PUBLIC_SUPABASE_URL)
        console.log("Current environment:", process.env.NODE_ENV)
        
        const { data, error } = await supabase
          .from('profiles')
          .select('*')
          .eq('id', user.id)
          .single()
        
        if (error) {
          console.error('Error fetching profile:', error)
          // Log additional details for debugging
          console.log('Error code:', error.code)
          console.log('Error details:', error.details)
          console.log('Error hint:', error.hint)
          
          // If the profile doesn't exist, create it
          if (error.code === 'PGRST116' || error.message.includes('not found')) {
            console.log('Profile not found, will create a new one on save')
            
            // Set some reasonable defaults
            if (user.email) {
              const usernameFromEmail = user.email.split('@')[0]
              form.reset({
                ...form.getValues(),
                username: usernameFromEmail
              })
            }
          }
          // Don't return early, fall through to set default values
        }
        
        if (data) {
          console.log("Profile data retrieved:", data)
          form.reset({
            username: data.username || "",
            fullName: data.full_name || "",
            bio: data.bio || "",
            country: data.country || "",
            school: data.school || "",
            educationLevel: data.education_level || undefined,
            interests: data.interests || [],
            conferenceExperience: data.conference_experience || [],
          })
          
          setSelectedInterests(data.interests || [])
          setConferenceExperience(data.conference_experience || [])
          setAvatarUrl(data.avatar_url)
        } else {
          // If no profile data, set defaults based on user info
          console.log("No profile data found, setting defaults")
          if (user.email) {
            const usernameFromEmail = user.email.split('@')[0]
            form.reset({
              ...form.getValues(),
              username: usernameFromEmail
            })
          }
        }
      } catch (error) {
        console.error('Error:', error)
        // Still proceed with empty form that user can fill out
      } finally {
        setIsFetching(false)
      }
    }
    
    fetchProfile()
    
    // Prefetch the conferences page to make navigation smoother
    router.prefetch('/conferences')
    
  }, [user, form, router])

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

  const handleAvatarUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    try {
      setUploading(true)
      // Show a toast to let the user know upload is in progress
      toast({
        title: "Uploading...",
        description: "Your profile picture is being uploaded.",
      })
      
      if (!event.target.files || event.target.files.length === 0) {
        throw new Error('You must select an image to upload.')
      }
      
      if (!user) {
        throw new Error('You must be logged in to upload an avatar.')
      }
      
      if (!supabase) {
        throw new Error('Supabase client is not initialized.')
      }
      
      const file = event.target.files[0]
      const fileExt = file.name.split('.').pop()?.toLowerCase()
      
      // Validate file type
      const validTypes = ['jpg', 'jpeg', 'png', 'gif', 'webp']
      if (!fileExt || !validTypes.includes(fileExt)) {
        throw new Error('Invalid file type. Please upload a JPG, PNG, GIF, or WebP image.')
      }
      
      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        throw new Error('File size too large. Please upload an image smaller than 5MB.')
      }
      
      const filePath = `${user.id}-${Math.random()}.${fileExt}`
      console.log('Uploading avatar to path:', filePath)
      console.log('Using Supabase URL:', process.env.NEXT_PUBLIC_SUPABASE_URL)
      
      try {
        // Upload file to Supabase Storage
        const { error: uploadError } = await supabase.storage
          .from('avatars')
          .upload(filePath, file, {
            cacheControl: '3600',
            upsert: true
          })
          
        if (uploadError) {
          console.error('Storage upload error:', uploadError)
          throw new Error(uploadError.message || 'Error uploading file')
        }
        
        // Get public URL
        const { data } = supabase.storage.from('avatars').getPublicUrl(filePath)
        
        if (data?.publicUrl) {
          setAvatarUrl(data.publicUrl)
          toast({
            title: "Avatar uploaded",
            description: "Your profile picture has been updated successfully!",
          })
        } else {
          throw new Error('Could not get public URL for uploaded file')
        }
      } catch (storageError) {
        console.error('Storage error:', storageError)
        throw storageError
      }
    } catch (error) {
      console.error('Avatar upload error:', error)
      toast({
        variant: "destructive",
        title: "Upload failed",
        description: error instanceof Error ? error.message : "An unexpected error occurred",
      })
    } finally {
      setUploading(false)
    }
  }

  // Add a function to store profile data in localStorage as a fallback
  const saveProfileToLocalStorage = (profileData: any) => {
    try {
      localStorage.setItem('profile_data', JSON.stringify(profileData));
      return true;
    } catch (error) {
      console.error('Error saving to localStorage:', error);
      return false;
    }
  };

  // Add a function to load profile data from localStorage
  const loadProfileFromLocalStorage = () => {
    try {
      const data = localStorage.getItem('profile_data');
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Error loading from localStorage:', error);
      return null;
    }
  };

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

    if (!supabase) {
      toast({
        variant: "destructive",
        title: "Connection error",
        description: "Cannot connect to the database. Please try again later.",
      })
      return
    }

    setIsLoading(true)
    try {
      console.log("Updating profile for user:", user.id)
      console.log("Environment:", process.env.NODE_ENV)
      console.log("Supabase URL:", process.env.NEXT_PUBLIC_SUPABASE_URL)
      
      // Before upserting, check if username is unique (if changed)
      if (form.formState.dirtyFields.username) {
        try {
          const { data, error } = await supabase
            .from('profiles')
            .select('id')
            .eq('username', values.username)
            .neq('id', user.id) // Exclude current user
            .maybeSingle();
          
          if (error) {
            console.error('Error checking username uniqueness:', error);
          } else if (data) {
            // Username exists for another user
            toast({
              variant: "destructive",
              title: "Username taken",
              description: "This username is already in use. Please choose another one.",
            });
            form.setError('username', { 
              type: 'manual', 
              message: 'Username already taken' 
            });
            setIsLoading(false);
            return;
          }
        } catch (error) {
          console.error('Error checking username uniqueness:', error);
        }
      }

      // Prepare the profile data
      const profileData = {
        id: user.id,
        username: values.username,
        full_name: values.fullName || null,
        bio: values.bio || null,
        country: values.country || null,
        school: values.school || null,
        education_level: values.educationLevel || null,
        interests: selectedInterests,
        conference_experience: conferenceExperience,
        avatar_url: avatarUrl,
        updated_at: new Date().toISOString(),
      };
      
      console.log("Profile data being sent:", profileData);
      
      try {
        // Update the profile in Supabase
        const { error } = await supabase
          .from('profiles')
          .upsert(profileData, { 
            onConflict: 'id'
          });
        
        if (error) {
          console.error('Error updating profile:', error)
          console.log('Error code:', error.code)
          console.log('Error details:', error.details)
          console.log('Error hint:', error.hint)
          
          // For production, show appropriate error message
          if (isVercel || process.env.NODE_ENV === 'production') {
            toast({
              variant: "destructive",
              title: "Profile update failed",
              description: `Error: ${error.message}. Please try again later.`,
            });
          } else {
            // For development, store locally as fallback
            const saved = saveProfileToLocalStorage(profileData);
            
            if (saved) {
              toast({
                title: "Development Mode - Profile Saved Locally",
                description: `Database error: ${error.message}. Your profile has been saved locally for development.`,
              });
            } else {
              toast({
                variant: "destructive",
                title: "Profile update failed",
                description: `Error: ${error.message}. Could not save profile.`,
              });
            }
          }
          return;
        }
        
        // Success!
        toast({
          title: "Profile updated",
          description: "Your profile has been updated successfully!",
        });
      } catch (submitError) {
        console.error('Exception during profile update:', submitError);
        // Show error message
        toast({
          variant: "destructive",
          title: "Something went wrong",
          description: submitError instanceof Error ? submitError.message : "An unexpected error occurred",
        });
      }
    } catch (error) {
      console.error('Error in profile update:', error);
      toast({
        variant: "destructive",
        title: "Something went wrong",
        description: error instanceof Error ? error.message : "Please try again later.",
      });
    } finally {
      setIsLoading(false);
    }
  }

  const navigateToConferencesPage = () => {
    router.push("/conferences")
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
      <h1 className="text-3xl font-bold mb-8 bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">My Profile</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1">
          <Card>
            <CardHeader>
              <div className="flex flex-col items-center">
                <Avatar className="h-24 w-24 mb-4">
                  <AvatarImage src={avatarUrl || "/placeholder.svg?height=96&width=96"} alt={form.getValues("username")} />
                  <AvatarFallback className="text-lg">
                    {form.getValues("username").substring(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <CardTitle>{form.getValues("fullName") || form.getValues("username")}</CardTitle>
                <CardDescription className="mt-1 text-center">
                  {form.getValues("bio")?.substring(0, 100) || "No bio provided"}
                  {form.getValues("bio") && form.getValues("bio")!.length > 100 ? "..." : ""}
                </CardDescription>
                
                <div className="mt-4 w-full">
                  <label htmlFor="avatar-upload" className="w-full">
                    <div className="flex items-center justify-center w-full cursor-pointer">
                      <Button variant="outline" className="mt-2 w-full" disabled={uploading}>
                        <Upload className="h-4 w-4 mr-2" />
                        {uploading ? "Uploading..." : "Upload Picture"}
                      </Button>
                    </div>
                    <input
                      id="avatar-upload"
                      type="file"
                      accept="image/*"
                      onChange={handleAvatarUpload}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>
            </CardHeader>
            <CardContent className="mt-2">
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-blue-600" />
                  <span>{form.getValues("country") || "No country specified"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-blue-600" />
                  <span>{form.getValues("school") || "No school specified"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <GraduationCap className="h-4 w-4 text-blue-600" />
                  <span>
                    {EDUCATION_LEVELS.find(level => level.id === form.getValues("educationLevel"))?.name || "Education level not specified"}
                  </span>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button 
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                onClick={navigateToConferencesPage}
              >
                Manage Conferences
              </Button>
            </CardFooter>
          </Card>
        </div>
        
        <div className="md:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Edit Profile</CardTitle>
              <CardDescription>
                Update your profile information and preferences
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="basic" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="basic">Basic Info</TabsTrigger>
                  <TabsTrigger value="education">Education</TabsTrigger>
                  <TabsTrigger value="interests">Interests</TabsTrigger>
                </TabsList>
                
                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                    <TabsContent value="basic" className="space-y-4 mt-4">
                      <FormField
                        control={form.control}
                        name="username"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Username</FormLabel>
                            <FormControl>
                              <Input placeholder="username" {...field} />
                            </FormControl>
                            <FormDescription>
                              This is your public display name
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
                              <Input placeholder="John Doe" {...field} value={field.value || ""} />
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
                                placeholder="Tell us about yourself"
                                className="resize-none"
                                {...field}
                                value={field.value || ""}
                              />
                            </FormControl>
                            <FormDescription>
                              Maximum 300 characters
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
                              defaultValue={field.value || ""}
                            >
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue placeholder="Select a country" />
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
                    </TabsContent>
                    
                    <TabsContent value="education" className="space-y-4 mt-4">
                      <FormField
                        control={form.control}
                        name="school"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>School</FormLabel>
                            <FormControl>
                              <Input placeholder="Your school name" {...field} value={field.value || ""} />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      
                      <FormField
                        control={form.control}
                        name="educationLevel"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Education Level</FormLabel>
                            <Select
                              onValueChange={field.onChange}
                              defaultValue={field.value}
                            >
                              <FormControl>
                                <SelectTrigger>
                                  <SelectValue placeholder="Select education level" />
                                </SelectTrigger>
                              </FormControl>
                              <SelectContent>
                                {EDUCATION_LEVELS.map((level) => (
                                  <SelectItem key={level.id} value={level.id}>
                                    {level.name}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      
                      <div className="space-y-4">
                        <div>
                          <h3 className="text-sm font-medium mb-2">Conference Experience</h3>
                          <div className="flex">
                            <Input
                              placeholder="Add a conference"
                              value={newConference}
                              onChange={(e) => setNewConference(e.target.value)}
                              className="rounded-r-none"
                            />
                            <Button
                              type="button"
                              onClick={addConference}
                              className="rounded-l-none bg-blue-600 hover:bg-blue-700"
                            >
                              Add
                            </Button>
                          </div>
                        </div>
                        
                        <div className="flex flex-wrap gap-2 mt-2">
                          {conferenceExperience.map((conference, index) => (
                            <div
                              key={index}
                              className="flex items-center bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 px-3 py-1 rounded-full text-sm"
                            >
                              {conference}
                              <button
                                type="button"
                                onClick={() => removeConference(conference)}
                                className="ml-2 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200"
                              >
                                &times;
                              </button>
                            </div>
                          ))}
                          {conferenceExperience.length === 0 && (
                            <p className="text-sm text-gray-500">No conferences added yet</p>
                          )}
                        </div>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="interests" className="space-y-4 mt-4">
                      <div className="space-y-4">
                        <h3 className="text-sm font-medium">Interests</h3>
                        <div className="flex flex-wrap gap-2">
                          {INTERESTS.map((interest) => (
                            <div
                              key={interest}
                              onClick={() => handleInterestToggle(interest)}
                              className={`cursor-pointer px-3 py-1 rounded-full text-sm border ${
                                selectedInterests.includes(interest)
                                  ? "bg-blue-100 border-blue-300 text-blue-800 dark:bg-blue-900/30 dark:border-blue-800 dark:text-blue-300"
                                  : "bg-gray-100 border-gray-300 text-gray-800 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300"
                              }`}
                            >
                              {selectedInterests.includes(interest) && (
                                <CheckCircle className="inline-block w-3 h-3 mr-1" />
                              )}
                              {interest}
                            </div>
                          ))}
                        </div>
                      </div>
                    </TabsContent>
                    
                    <div className="pt-4 border-t">
                      <Button
                        type="submit"
                        className="w-full md:w-auto bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
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
                    </div>
                  </form>
                </Form>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
} 