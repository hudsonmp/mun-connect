"use client"

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle,
  DialogFooter,
  DialogTrigger
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { useToast } from '@/components/ui/use-toast'
import { useUserProfile } from '@/lib/user-profile-context'
import { ChevronRight, ArrowRight, UserCog } from 'lucide-react'
import { UserInterest, UserExperience } from '@/lib/user-profile-context'

interface OnboardingModalProps {
  buttonTrigger?: boolean;
}

export function OnboardingModal({ buttonTrigger = false }: OnboardingModalProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [open, setOpen] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    interests: [] as UserInterest[],
    experience: null as UserExperience | null,
    projectName: '',
    projectGoals: '',
    projectTimeline: 'long' as 'short' | 'medium' | 'long',
    selectedFeatures: [] as string[]
  })
  
  const { profile, isLoading, submitOnboarding } = useUserProfile()
  const { toast } = useToast()
  const router = useRouter()
  
  // Force open modal if user hasn't completed onboarding
  useEffect(() => {
    if (!isLoading && profile) {
      // Always check and force onboarding for existing users (unless explicitly triggered by button)
      if (!profile.hasCompletedOnboarding && !buttonTrigger) {
        setOpen(true)
      }
      
      // Pre-fill form data if available
      setFormData(prev => ({
        ...prev,
        name: profile.name || prev.name,
        email: profile.email || prev.email,
        interests: profile.interests.length > 0 ? profile.interests : prev.interests,
        experience: profile.experience || prev.experience,
        projectName: profile.projectName || prev.projectName,
        projectGoals: profile.projectGoals || prev.projectGoals,
        projectTimeline: profile.projectTimeline || prev.projectTimeline,
        selectedFeatures: profile.selectedFeatures.length > 0 ? profile.selectedFeatures : prev.selectedFeatures
      }))
    }
  }, [isLoading, profile, buttonTrigger])
  
  // Handle step transitions
  const handleNext = () => {
    // Validate current step before advancing
    if (currentStep === 0) {
      if (!formData.name.trim()) {
        toast({
          title: "Name required",
          description: "Please enter your name to continue.",
          variant: "destructive"
        })
        return
      }
      if (!formData.email.trim() || !formData.email.includes('@')) {
        toast({
          title: "Valid email required",
          description: "Please enter a valid email address to continue.",
          variant: "destructive"
        })
        return
      }
    } else if (currentStep === 1) {
      if (formData.interests.length === 0) {
        toast({
          title: "Select interests",
          description: "Please select at least one interest to continue.",
          variant: "destructive"
        })
        return
      }
    } else if (currentStep === 2) {
      if (!formData.experience) {
        toast({
          title: "Select experience level",
          description: "Please select your experience level to continue.",
          variant: "destructive"
        })
        return
      }
    }
    
    setCurrentStep(prev => prev + 1)
  }
  
  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1)
    }
  }
  
  const handleComplete = async () => {
    try {
      // Validate project info
      if (!formData.projectName.trim()) {
        toast({
          title: "Project name required",
          description: "Please enter a name for your project.",
          variant: "destructive"
        })
        return
      }
      
      const success = await submitOnboarding({
        name: formData.name,
        interests: formData.interests,
        experience: formData.experience,
        projectName: formData.projectName,
        projectGoals: formData.projectGoals || null,
        projectTimeline: formData.projectTimeline,
        selectedFeatures: formData.selectedFeatures
      })
      
      if (success) {
        toast({
          title: "Onboarding complete!",
          description: "Your profile has been set up successfully."
        })
        setOpen(false)
        // Refresh the page to update the UI state
        router.refresh()
      } else {
        toast({
          title: "Error",
          description: "Failed to complete onboarding. Please try again.",
          variant: "destructive"
        })
      }
    } catch (error) {
      console.error('Onboarding error:', error)
      toast({
        title: "Error",
        description: "An unexpected error occurred. Please try again.",
        variant: "destructive"
      })
    }
  }
  
  // Toggle interest selection
  const toggleInterest = (interest: UserInterest) => {
    setFormData(prev => {
      const isSelected = prev.interests.includes(interest)
      return {
        ...prev,
        interests: isSelected 
          ? prev.interests.filter(i => i !== interest)
          : [...prev.interests, interest]
      }
    })
  }
  
  // Toggle feature selection
  const toggleFeature = (feature: string) => {
    setFormData(prev => {
      const isSelected = prev.selectedFeatures.includes(feature)
      return {
        ...prev,
        selectedFeatures: isSelected 
          ? prev.selectedFeatures.filter(f => f !== feature)
          : [...prev.selectedFeatures, feature]
      }
    })
  }
  
  // Handle input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }
  
  // Render step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <>
            <DialogHeader>
              <DialogTitle className="text-xl font-bold">Welcome to AI Chat</DialogTitle>
              <DialogDescription>
                Let&apos;s get to know you better to personalize your experience.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Your Name</Label>
                <Input 
                  id="name" 
                  name="name" 
                  placeholder="Enter your name" 
                  value={formData.name}
                  onChange={handleInputChange}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input 
                  id="email" 
                  name="email" 
                  type="email" 
                  placeholder="Enter your email" 
                  value={formData.email}
                  onChange={handleInputChange}
                />
              </div>
            </div>
            
            <DialogFooter>
              <Button onClick={handleNext} className="ml-auto">
                Next <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </DialogFooter>
          </>
        )
        
      case 1:
        return (
          <>
            <DialogHeader>
              <DialogTitle className="text-xl font-bold">Your Interests</DialogTitle>
              <DialogDescription>
                Select topics you&apos;re interested in discussing with the AI.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {["Artificial Intelligence", "Programming", "Design", "Business", "Education"].map((interest) => (
                  <div 
                    key={interest} 
                    className="flex items-center space-x-2"
                  >
                    <Checkbox 
                      id={interest} 
                      checked={formData.interests.includes(interest as UserInterest)}
                      onCheckedChange={() => toggleInterest(interest as UserInterest)}
                    />
                    <Label htmlFor={interest}>{interest}</Label>
                  </div>
                ))}
              </div>
            </div>
            
            <DialogFooter className="flex justify-between">
              <Button variant="outline" onClick={handleBack}>
                Back
              </Button>
              <Button onClick={handleNext}>
                Next <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </DialogFooter>
          </>
        )
        
      case 2:
        return (
          <>
            <DialogHeader>
              <DialogTitle className="text-xl font-bold">Your Experience</DialogTitle>
              <DialogDescription>
                How familiar are you with AI tools?
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <RadioGroup 
                value={formData.experience || ''} 
                onValueChange={(value) => setFormData(prev => ({
                  ...prev,
                  experience: value as UserExperience
                }))}
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="Beginner" id="beginner" />
                  <Label htmlFor="beginner">Beginner - I&apos;m new to AI tools</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="Intermediate" id="intermediate" />
                  <Label htmlFor="intermediate">Intermediate - I&apos;ve used AI tools before</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="Advanced" id="advanced" />
                  <Label htmlFor="advanced">Advanced - I&apos;m experienced with AI tools</Label>
                </div>
              </RadioGroup>
            </div>
            
            <DialogFooter className="flex justify-between">
              <Button variant="outline" onClick={handleBack}>
                Back
              </Button>
              <Button onClick={handleNext}>
                Next <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </DialogFooter>
          </>
        )
        
      case 3:
        return (
          <>
            <DialogHeader>
              <DialogTitle className="text-xl font-bold">Project Details</DialogTitle>
              <DialogDescription>
                Please provide some information about your project to help me understand your needs better.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="projectName">Project Name <span className="text-red-500">*</span></Label>
                <Input 
                  id="projectName" 
                  name="projectName" 
                  placeholder="Enter your project name" 
                  value={formData.projectName}
                  onChange={handleInputChange}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="projectGoals">Project Goals <span className="text-red-500">*</span></Label>
                <Input 
                  id="projectGoals" 
                  name="projectGoals" 
                  placeholder="What are you trying to achieve with this project?" 
                  value={formData.projectGoals}
                  onChange={handleInputChange}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="projectTimeline">Project Timeline <span className="text-red-500">*</span></Label>
                <RadioGroup 
                  value={formData.projectTimeline} 
                  onValueChange={(value) => setFormData(prev => ({
                    ...prev,
                    projectTimeline: value as 'short' | 'medium' | 'long'
                  }))}
                >
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="short" id="short" />
                    <Label htmlFor="short">Short term (under 1 month)</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="medium" id="medium" />
                    <Label htmlFor="medium">Medium term (1-3 months)</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <RadioGroupItem value="long" id="long" />
                    <Label htmlFor="long">Long term (3+ months)</Label>
                  </div>
                </RadioGroup>
              </div>
              
              <div className="space-y-2">
                <Label>Key Features</Label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {[
                    "User Authentication", 
                    "Database Integration", 
                    "API Integration", 
                    "Responsive Design",
                    "Analytics"
                  ].map((feature) => (
                    <div 
                      key={feature} 
                      className="flex items-center space-x-2"
                    >
                      <Checkbox 
                        id={feature} 
                        checked={formData.selectedFeatures.includes(feature)}
                        onCheckedChange={() => toggleFeature(feature)}
                      />
                      <Label htmlFor={feature}>{feature}</Label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            
            <DialogFooter className="flex justify-between">
              <Button variant="outline" onClick={handleBack}>
                Back
              </Button>
              <Button onClick={handleComplete}>
                Complete <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </DialogFooter>
          </>
        )
        
      default:
        return null
    }
  }
  
  // Prevent closing the modal if onboarding is not complete
  const handleOpenChange = (openState: boolean) => {
    // Only allow closing if onboarding is complete or triggered by button
    if (!openState && profile && !profile.hasCompletedOnboarding && !buttonTrigger) {
      toast({
        title: "Onboarding Required",
        description: "Please complete the onboarding process to continue.",
        variant: "destructive"
      })
      return;
    }
    
    setOpen(openState)
  }
  
  const modalContent = (
    <DialogContent className="sm:max-w-[500px] overflow-y-auto max-h-[90vh]">
      {renderStepContent()}
    </DialogContent>
  );
  
  // If it's a button trigger, use the DialogTrigger component
  if (buttonTrigger) {
    return (
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="sm" className="flex items-center gap-2">
            <UserCog className="h-5 w-5" />
            <span>Profile Setup</span>
          </Button>
        </DialogTrigger>
        {modalContent}
      </Dialog>
    );
  }
  
  // Otherwise, just render the dialog with forced open state
  return (
    <Dialog 
      open={open} 
      onOpenChange={handleOpenChange}
      modal={true}
    >
      {modalContent}
    </Dialog>
  )
} 