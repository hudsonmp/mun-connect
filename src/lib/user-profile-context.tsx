"use client"

import React, { createContext, useContext, useState, useEffect } from "react"
import { useAuth } from "./auth-context"
import { supabase } from "./supabase-client"

// Define user profile types
export type UserInterest = 
  | "Artificial Intelligence" 
  | "Programming" 
  | "Design" 
  | "Business" 
  | "Education"

export type UserExperience = 
  | "Beginner" 
  | "Intermediate" 
  | "Advanced"

export interface UserProfile {
  id: string
  name: string
  email: string
  hasCompletedOnboarding: boolean
  interests: UserInterest[]
  experience: UserExperience | null
  projectName: string | null
  projectGoals: string | null
  projectTimeline: "short" | "medium" | "long" | null
  selectedFeatures: string[]
}

interface UserProfileContextProps {
  profile: UserProfile | null
  isLoading: boolean
  error: string | null
  updateProfile: (data: Partial<UserProfile>) => Promise<void>
  submitOnboarding: (data: Partial<UserProfile>) => Promise<boolean>
  clearError: () => void
}

const defaultProfile: UserProfile = {
  id: "",
  name: "",
  email: "",
  hasCompletedOnboarding: false,
  interests: [],
  experience: null,
  projectName: null,
  projectGoals: null,
  projectTimeline: null,
  selectedFeatures: []
}

const UserProfileContext = createContext<UserProfileContextProps | undefined>(undefined)

export function UserProfileProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const clearError = () => setError(null)

  // Fetch user profile when authenticated
  useEffect(() => {
    if (!user) {
      setProfile(null)
      setIsLoading(false)
      return
    }

    async function fetchUserProfile() {
      try {
        setIsLoading(true)
        
        // Safe check to ensure user is not null (TS validation)
        const userId = user?.id
        if (!userId) {
          setIsLoading(false)
          return
        }
        
        const { data, error } = await supabase
          .from('user_profiles')
          .select('*')
          .eq('user_id', userId)
          .single()
        
        if (error) throw error

        if (data) {
          setProfile({
            id: userId,
            name: data.name || "",
            email: user.email || "",
            hasCompletedOnboarding: data.has_completed_onboarding || false,
            interests: data.interests || [],
            experience: data.experience || null,
            projectName: data.project_name || null,
            projectGoals: data.project_goals || null,
            projectTimeline: data.project_timeline || null,
            selectedFeatures: data.selected_features || []
          })
        } else {
          // Create a default profile if none exists
          setProfile({
            ...defaultProfile,
            id: userId,
            email: user.email || ""
          })
        }
      } catch (err) {
        console.error("Error fetching user profile:", err)
        setError(typeof err === 'object' && err !== null && 'message' in err 
          ? String(err.message) 
          : "Failed to load user profile")
      } finally {
        setIsLoading(false)
      }
    }

    fetchUserProfile()
  }, [user])

  // Update profile in database
  const updateProfile = async (data: Partial<UserProfile>) => {
    if (!user || !profile) return

    try {
      setError(null)
      
      // Update local state first for immediate UI feedback
      setProfile(current => current ? { ...current, ...data } : null)
      
      // Transform data for database
      const dbData = {
        user_id: user.id,
        name: data.name,
        has_completed_onboarding: data.hasCompletedOnboarding,
        interests: data.interests,
        experience: data.experience,
        project_name: data.projectName,
        project_goals: data.projectGoals,
        project_timeline: data.projectTimeline,
        selected_features: data.selectedFeatures
      }
      
      // Remove undefined values
      Object.keys(dbData).forEach(key => {
        if (dbData[key as keyof typeof dbData] === undefined) {
          delete dbData[key as keyof typeof dbData]
        }
      })
      
      // Upsert the profile
      const { error } = await supabase
        .from('user_profiles')
        .upsert(dbData, { onConflict: 'user_id' })
      
      if (error) throw error
    } catch (err) {
      console.error("Error updating profile:", err)
      setError(typeof err === 'object' && err !== null && 'message' in err 
        ? String(err.message) 
        : "Failed to update profile")
      
      // Revert profile to previous state on error
      if (user) {
        const { data } = await supabase
          .from('user_profiles')
          .select('*')
          .eq('user_id', user.id)
          .single()
        
        if (data) {
          setProfile({
            id: user.id,
            name: data.name || "",
            email: user.email || "",
            hasCompletedOnboarding: data.has_completed_onboarding || false,
            interests: data.interests || [],
            experience: data.experience || null,
            projectName: data.project_name || null,
            projectGoals: data.project_goals || null,
            projectTimeline: data.project_timeline || null,
            selectedFeatures: data.selected_features || []
          })
        }
      }
      
      throw err
    }
  }

  // Handle onboarding submission
  const submitOnboarding = async (data: Partial<UserProfile>) => {
    if (!user) return false

    try {
      setError(null)
      
      // Update profile with onboarding data
      await updateProfile({
        ...data,
        hasCompletedOnboarding: true
      })
      
      return true
    } catch (err) {
      console.error("Error submitting onboarding:", err)
      setError(typeof err === 'object' && err !== null && 'message' in err 
        ? String(err.message) 
        : "Failed to complete onboarding")
      return false
    }
  }

  const value = {
    profile,
    isLoading,
    error,
    updateProfile,
    submitOnboarding,
    clearError
  }

  return (
    <UserProfileContext.Provider value={value}>
      {children}
    </UserProfileContext.Provider>
  )
}

export const useUserProfile = () => {
  const context = useContext(UserProfileContext)
  if (context === undefined) {
    throw new Error("useUserProfile must be used within a UserProfileProvider")
  }
  return context
} 