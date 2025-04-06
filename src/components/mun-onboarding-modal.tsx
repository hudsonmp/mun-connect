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
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/components/ui/use-toast'
import { useMUNOnboarding } from '@/lib/mun-onboarding-context'
import { ChevronRight, ArrowRight, FileText } from 'lucide-react'

interface MUNOnboardingModalProps {
  buttonTrigger?: boolean;
}

export function MUNOnboardingModal({ buttonTrigger = false }: MUNOnboardingModalProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [open, setOpen] = useState(false)
  const [formData, setFormData] = useState({
    conferenceName: '',
    committeeName: '',
    positionCountry: '',
    topic: '',
    countryStance: '',
    keyPoints: ['', '', '']
  })
  
  const { munData, isLoading, submitMUNOnboarding } = useMUNOnboarding()
  const { toast } = useToast()
  const router = useRouter()
  
  // Force open modal if explicitly triggered or when there's no MUN data
  useEffect(() => {
    if (!isLoading && buttonTrigger) {
      setOpen(true)
    }
    
    // Pre-fill form data if available
    if (!isLoading && munData) {
      setFormData(prev => ({
        ...prev,
        conferenceName: munData.conferenceName || prev.conferenceName,
        committeeName: munData.committeeName || prev.committeeName,
        positionCountry: munData.positionCountry || prev.positionCountry,
        topic: munData.topic || prev.topic,
        countryStance: munData.countryStance || prev.countryStance,
        keyPoints: munData.keyPoints?.length > 0 
          ? [...munData.keyPoints.slice(0, 3), ...Array(Math.max(0, 3 - munData.keyPoints.length)).fill('')] 
          : prev.keyPoints
      }))
    }
  }, [isLoading, munData, buttonTrigger])
  
  // Pre-populate with mock data for testing
  const fillWithMockData = () => {
    setFormData({
      conferenceName: "Harvard National Model United Nations",
      committeeName: "United Nations Security Council",
      positionCountry: "France",
      topic: "Nuclear Non-Proliferation in the Middle East",
      countryStance: "As a permanent member of the UN Security Council and a nuclear power, France advocates for strict non-proliferation measures while supporting peaceful nuclear energy development.",
      keyPoints: [
        "Emphasize France's dedication to the Nuclear Non-Proliferation Treaty (NPT)",
        "Highlight commitment to diplomatic solutions over military interventions",
        "Stress the importance of IAEA inspections and monitoring mechanisms"
      ]
    })
  }
  
  // Handle step transitions
  const handleNext = () => {
    // Validate current step before advancing
    if (currentStep === 0) {
      if (!formData.conferenceName.trim() || !formData.committeeName.trim()) {
        toast({
          title: "Required fields missing",
          description: "Please fill in all required fields to continue.",
          variant: "destructive"
        })
        return
      }
    } else if (currentStep === 1) {
      if (!formData.positionCountry.trim() || !formData.topic.trim()) {
        toast({
          title: "Required fields missing",
          description: "Please fill in all required fields to continue.",
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
      // Filter out empty key points
      const keyPoints = formData.keyPoints.filter(point => point.trim() !== '')
      
      const success = await submitMUNOnboarding({
        conferenceName: formData.conferenceName,
        committeeName: formData.committeeName,
        positionCountry: formData.positionCountry,
        topic: formData.topic,
        countryStance: formData.countryStance,
        keyPoints
      })
      
      if (success) {
        toast({
          title: "MUN data saved!",
          description: "Your MUN position information has been saved successfully."
        })
        setOpen(false)
        router.refresh()
      } else {
        toast({
          title: "Error",
          description: "Failed to save MUN data. Please try again.",
          variant: "destructive"
        })
      }
    } catch (error) {
      console.error('MUN onboarding error:', error)
      toast({
        title: "Error",
        description: "An unexpected error occurred. Please try again.",
        variant: "destructive"
      })
    }
  }
  
  // Handle input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }
  
  // Handle key point changes
  const handleKeyPointChange = (index: number, value: string) => {
    setFormData(prev => {
      const newKeyPoints = [...prev.keyPoints]
      newKeyPoints[index] = value
      return {
        ...prev,
        keyPoints: newKeyPoints
      }
    })
  }
  
  // Render step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <>
            <DialogHeader>
              <DialogTitle className="text-xl font-bold">MUN Conference Details</DialogTitle>
              <DialogDescription>
                Tell us about the MUN conference you&apos;re participating in.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="conferenceName">Conference Name <span className="text-red-500">*</span></Label>
                <Input 
                  id="conferenceName" 
                  name="conferenceName" 
                  placeholder="e.g., Harvard Model United Nations" 
                  value={formData.conferenceName}
                  onChange={handleInputChange}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="committeeName">Committee Name <span className="text-red-500">*</span></Label>
                <Input 
                  id="committeeName" 
                  name="committeeName" 
                  placeholder="e.g., United Nations Security Council" 
                  value={formData.committeeName}
                  onChange={handleInputChange}
                />
              </div>
              
              <div className="mt-6">
                <Button 
                  type="button" 
                  variant="outline" 
                  size="sm" 
                  onClick={fillWithMockData}
                >
                  Fill with Test Data
                </Button>
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
              <DialogTitle className="text-xl font-bold">Your Position Details</DialogTitle>
              <DialogDescription>
                Provide information about your country assignment and topic.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="positionCountry">Country/Position <span className="text-red-500">*</span></Label>
                <Input 
                  id="positionCountry" 
                  name="positionCountry" 
                  placeholder="e.g., France, NGO, etc." 
                  value={formData.positionCountry}
                  onChange={handleInputChange}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="topic">Topic/Agenda <span className="text-red-500">*</span></Label>
                <Input 
                  id="topic" 
                  name="topic" 
                  placeholder="e.g., Nuclear Non-Proliferation" 
                  value={formData.topic}
                  onChange={handleInputChange}
                />
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
              <DialogTitle className="text-xl font-bold">Country Stance & Key Points</DialogTitle>
              <DialogDescription>
                Describe your country&apos;s position on the topic and key arguments.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="countryStance">Country&apos;s Stance</Label>
                <Textarea 
                  id="countryStance" 
                  name="countryStance" 
                  placeholder="Describe your country's position on this issue..." 
                  rows={4}
                  value={formData.countryStance}
                  onChange={handleInputChange}
                />
              </div>
              
              <div className="space-y-3 mt-3">
                <Label>Key Points (up to 3)</Label>
                {[0, 1, 2].map((index) => (
                  <Input 
                    key={index}
                    placeholder={`Key point ${index + 1}`}
                    value={formData.keyPoints[index] || ''}
                    onChange={(e) => handleKeyPointChange(index, e.target.value)}
                  />
                ))}
              </div>
            </div>
            
            <DialogFooter className="flex justify-between">
              <Button variant="outline" onClick={handleBack}>
                Back
              </Button>
              <Button onClick={handleComplete}>
                Save <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </DialogFooter>
          </>
        )
        
      default:
        return null
    }
  }
  
  // Handle open/close of the modal
  const handleOpenChange = (openState: boolean) => {
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
          <Button variant="outline" size="sm" className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            <span>Setup MUN Position</span>
          </Button>
        </DialogTrigger>
        {modalContent}
      </Dialog>
    );
  }
  
  // Otherwise, just render the dialog with current open state
  return (
    <Dialog 
      open={open} 
      onOpenChange={handleOpenChange}
    >
      {modalContent}
    </Dialog>
  )
} 