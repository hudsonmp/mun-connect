"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Calendar, Clock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/components/ui/use-toast"
import { useAuth } from "@/lib/auth-context"

export interface ConferenceFormProps {
  onSuccess?: () => void
  onCancel?: () => void
}

export function ConferenceForm({ onSuccess, onCancel }: ConferenceFormProps) {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const [formData, setFormData] = useState({
    name: "",
    acronym: "",
    dates: "",
    committee: "",
    committee_type: "GA", // GA, SC, crisis, specialized, other
    country: "",
    role: "",
    topic: "",
    location: "",
    status: "upcoming", // active, upcoming, completed
    progress: 0
  })

  // Debug user state
  useEffect(() => {
    console.log("Auth state in ConferenceForm:", { user, isLoading })
  }, [user, isLoading])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleRadioChange = (name: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!user || !user.id) {
      console.error("User not authenticated or missing ID:", user)
      toast({
        title: "Authentication required",
        description: "Please sign in to add a conference",
        variant: "destructive",
      })
      return
    }
    
    if (!formData.name.trim()) {
      toast({
        title: "Conference name required",
        description: "Please enter a conference name",
        variant: "destructive",
      })
      return
    }
    
    setIsSubmitting(true)
    console.log("Submitting with user ID:", user.id)
    
    try {
      const response = await fetch("/api/conferences", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "user-id": user.id,
        },
        body: JSON.stringify({
          ...formData,
          user_id: user.id, // Also include in the body as a fallback
        }),
      })
      
      if (!response.ok) {
        const error = await response.json()
        console.error("Conference creation error:", error)
        throw new Error(error.error || "Failed to create conference")
      }
      
      toast({
        title: "Conference added",
        description: "Your conference has been added successfully",
      })
      
      router.refresh()
      
      if (onSuccess) {
        onSuccess()
      }
    } catch (error: any) {
      console.error("Conference creation exception:", error)
      toast({
        title: "Error adding conference",
        description: error.message || "An unexpected error occurred",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }
  
  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Add New Conference</CardTitle>
        <CardDescription>
          Enter the details of your MUN conference
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Conference Name *</Label>
            <Input
              id="name"
              name="name"
              placeholder="Harvard National Model United Nations"
              value={formData.name}
              onChange={handleChange}
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="acronym">Conference Acronym</Label>
            <Input
              id="acronym"
              name="acronym"
              placeholder="HNMUN"
              value={formData.acronym}
              onChange={handleChange}
            />
            <p className="text-xs text-muted-foreground">
              Common abbreviation for the conference, if any
            </p>
          </div>
          
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="dates">Conference Dates</Label>
              <div className="relative">
                <Input
                  id="dates"
                  name="dates"
                  placeholder="Feb 10-13, 2025"
                  value={formData.dates}
                  onChange={handleChange}
                />
                <Calendar className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground" />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="location">Location</Label>
              <Input
                id="location"
                name="location"
                placeholder="Boston, MA"
                value={formData.location}
                onChange={handleChange}
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="committee">Committee</Label>
            <Input
              id="committee"
              name="committee"
              placeholder="UN Security Council"
              value={formData.committee}
              onChange={handleChange}
            />
          </div>
          
          <div className="space-y-2">
            <Label>Committee Type</Label>
            <RadioGroup
              value={formData.committee_type}
              onValueChange={(value: string) => handleRadioChange("committee_type", value)}
              className="flex flex-wrap gap-4"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="GA" id="GA" />
                <Label htmlFor="GA" className="font-normal">General Assembly</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="SC" id="SC" />
                <Label htmlFor="SC" className="font-normal">Security Council</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="crisis" id="crisis" />
                <Label htmlFor="crisis" className="font-normal">Crisis</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="specialized" id="specialized" />
                <Label htmlFor="specialized" className="font-normal">Specialized</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="other" id="other" />
                <Label htmlFor="other" className="font-normal">Other</Label>
              </div>
            </RadioGroup>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="topic">Committee Topic</Label>
            <Input
              id="topic"
              name="topic"
              placeholder="Global Climate Crisis"
              value={formData.topic}
              onChange={handleChange}
            />
          </div>
          
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="country">Country/Character</Label>
              <Input
                id="country"
                name="country"
                placeholder="France"
                value={formData.country}
                onChange={handleChange}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="role">Your Role</Label>
              <Input
                id="role"
                name="role"
                placeholder="Delegate"
                value={formData.role}
                onChange={handleChange}
              />
            </div>
          </div>
          
          <div className="space-y-2">
            <Label>Conference Status</Label>
            <RadioGroup
              value={formData.status}
              onValueChange={(value: string) => handleRadioChange("status", value)}
              className="flex space-x-4"
            >
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="active" id="active" />
                <Label htmlFor="active" className="font-normal">Current</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="upcoming" id="upcoming" />
                <Label htmlFor="upcoming" className="font-normal">Upcoming</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="completed" id="completed" />
                <Label htmlFor="completed" className="font-normal">Past</Label>
              </div>
            </RadioGroup>
          </div>
        </CardContent>
        <CardFooter className="flex justify-between">
          <Button variant="outline" type="button" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting || isLoading}>
            {isSubmitting ? "Adding..." : "Add Conference"}
          </Button>
        </CardFooter>
      </form>
    </Card>
  )
} 