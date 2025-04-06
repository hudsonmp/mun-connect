"use client"

import React, { createContext, useContext, useState, useEffect } from "react"
import { useAuth } from "./auth-context"
import { supabase } from "./supabase-client"

// Define MUN-specific onboarding types
export interface MUNOnboardingData {
  id: string
  conferenceName: string
  committeeName: string
  positionCountry: string
  topic: string
  countryStance: string | null
  keyPoints: string[]
  researchMaterials: Record<string, any> | null
  backgroundInfo: string | null
  formattingPreferences: Record<string, any> | null
}

interface MUNOnboardingContextProps {
  munData: MUNOnboardingData | null
  isLoading: boolean
  error: string | null
  updateMUNData: (data: Partial<MUNOnboardingData>) => Promise<void>
  submitMUNOnboarding: (data: Partial<MUNOnboardingData>) => Promise<boolean>
  clearError: () => void
}

const defaultMUNData: MUNOnboardingData = {
  id: "",
  conferenceName: "Model United Nations Conference",
  committeeName: "United Nations Security Council",
  positionCountry: "France",
  topic: "Nuclear Non-Proliferation in the Middle East",
  countryStance: null,
  keyPoints: [],
  researchMaterials: null,
  backgroundInfo: null,
  formattingPreferences: null
}

const MUNOnboardingContext = createContext<MUNOnboardingContextProps | undefined>(undefined)

export function MUNOnboardingProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const [munData, setMUNData] = useState<MUNOnboardingData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const clearError = () => setError(null)

  // Fetch MUN onboarding data when authenticated
  useEffect(() => {
    if (!user) {
      setMUNData(null)
      setIsLoading(false)
      return
    }

    async function fetchMUNData() {
      try {
        setIsLoading(true)
        
        // Safe check to ensure user is not null (TS validation)
        const userId = user?.id
        if (!userId) {
          setIsLoading(false)
          return
        }
        
        const { data, error } = await supabase
          .from('mun_onboarding_data')
          .select('*')
          .eq('user_id', userId)
          .single()
        
        if (error && error.code !== 'PGRST116') { // PGRST116 = row not found
          throw error
        }

        if (data) {
          setMUNData({
            id: userId,
            conferenceName: data.conference_name,
            committeeName: data.committee_name,
            positionCountry: data.position_country,
            topic: data.topic,
            countryStance: data.country_stance,
            keyPoints: data.key_points || [],
            researchMaterials: data.research_materials || null,
            backgroundInfo: data.background_info || null,
            formattingPreferences: data.formatting_preferences || null
          })
        } else {
          // Create default MUN data if none exists
          setMUNData({
            ...defaultMUNData,
            id: userId
          })
        }
      } catch (err) {
        console.error("Error fetching MUN onboarding data:", err)
        setError(typeof err === 'object' && err !== null && 'message' in err 
          ? String(err.message) 
          : "Failed to load MUN onboarding data")
      } finally {
        setIsLoading(false)
      }
    }

    fetchMUNData()
  }, [user])

  // Update MUN data in database
  const updateMUNData = async (data: Partial<MUNOnboardingData>) => {
    if (!user || !munData) return

    try {
      setError(null)
      
      // Update local state first for immediate UI feedback
      setMUNData(current => current ? { ...current, ...data } : null)
      
      // Transform data for database
      const dbData = {
        user_id: user.id,
        conference_name: data.conferenceName,
        committee_name: data.committeeName,
        position_country: data.positionCountry,
        topic: data.topic,
        country_stance: data.countryStance,
        key_points: data.keyPoints,
        research_materials: data.researchMaterials,
        background_info: data.backgroundInfo,
        formatting_preferences: data.formattingPreferences
      }
      
      // Remove undefined values
      Object.keys(dbData).forEach(key => {
        if (dbData[key as keyof typeof dbData] === undefined) {
          delete dbData[key as keyof typeof dbData]
        }
      })
      
      // Upsert the MUN data
      const { error } = await supabase
        .from('mun_onboarding_data')
        .upsert(dbData, { onConflict: 'user_id' })
      
      if (error) throw error
    } catch (err) {
      console.error("Error updating MUN data:", err)
      setError(typeof err === 'object' && err !== null && 'message' in err 
        ? String(err.message) 
        : "Failed to update MUN data")
      
      // Revert MUN data to previous state on error
      if (user) {
        const { data } = await supabase
          .from('mun_onboarding_data')
          .select('*')
          .eq('user_id', user.id)
          .single()
        
        if (data) {
          setMUNData({
            id: user.id,
            conferenceName: data.conference_name,
            committeeName: data.committee_name,
            positionCountry: data.position_country,
            topic: data.topic,
            countryStance: data.country_stance,
            keyPoints: data.key_points || [],
            researchMaterials: data.research_materials || null,
            backgroundInfo: data.background_info || null,
            formattingPreferences: data.formatting_preferences || null
          })
        }
      }
      
      throw err
    }
  }

  // Handle MUN onboarding submission
  const submitMUNOnboarding = async (data: Partial<MUNOnboardingData>) => {
    if (!user) return false

    try {
      setError(null)
      
      // Update MUN data with onboarding data
      await updateMUNData(data)
      
      return true
    } catch (err) {
      console.error("Error submitting MUN onboarding:", err)
      setError(typeof err === 'object' && err !== null && 'message' in err 
        ? String(err.message) 
        : "Failed to complete MUN onboarding")
      return false
    }
  }

  const value = {
    munData,
    isLoading,
    error,
    updateMUNData,
    submitMUNOnboarding,
    clearError
  }

  return (
    <MUNOnboardingContext.Provider value={value}>
      {children}
    </MUNOnboardingContext.Provider>
  )
}

export const useMUNOnboarding = () => {
  const context = useContext(MUNOnboardingContext)
  if (context === undefined) {
    throw new Error("useMUNOnboarding must be used within a MUNOnboardingProvider")
  }
  return context
} 