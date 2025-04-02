"use client"

import React, { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useDropzone, FileRejection } from 'react-dropzone'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Stepper, Step, StepLabel, StepContent } from '@/components/ui/stepper'
import { useToast } from '@/components/ui/use-toast'
import { ChevronLeft, ChevronRight, FileUp, Loader2, CheckCircle, X } from 'lucide-react'
import countries from '@/lib/countries'
import { Badge } from '@/components/ui/badge'

// Sample data for UI
const popularTopics = [
  'Climate Change',
  'Human Rights',
  'Nuclear Disarmament',
  'Sustainable Development',
  'Refugees',
  'Cybersecurity',
  'Terrorism',
  'COVID-19 Response',
  'Economic Inequality',
  'Gender Equality'
]

// Helper function to parse topics from text
const parseTopicsFromText = (text: string): string[] => {
  if (!text.trim()) return []
  return text.split(',').map(topic => topic.trim()).filter(Boolean)
}

export interface OnboardingFlowProps {
  userId: string
  onComplete: () => void
}

export function OnboardingFlow({ userId, onComplete }: OnboardingFlowProps) {
  const [activeStep, setActiveStep] = useState(0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState({
    writingSample: '',
    preferredTopics: [] as string[],
    customTopics: '',
    preferredCountries: [] as string[],
    uploadedDocuments: [] as File[],
    delegateStyle: '',
    pastPapers: '',
    pastSpeeches: '',
    pastResolutions: ''
  })
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()
  const router = useRouter()
  
  // Dropzone setup
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt']
    },
    maxSize: 5 * 1024 * 1024, // 5MB
    onDrop: (acceptedFiles: File[]) => {
      setFormData(prev => ({
        ...prev,
        uploadedDocuments: [...prev.uploadedDocuments, ...acceptedFiles]
      }))
    },
    onDropRejected: (rejectedFiles: FileRejection[]) => {
      toast({
        title: "File upload failed",
        description: "Please ensure files are under 5MB and in a supported format (PDF, DOC, DOCX, TXT).",
        variant: "destructive",
      })
    }
  })
  
  const handleNext = () => {
    if (activeStep === 0 && formData.writingSample.length < 50 && formData.uploadedDocuments.length === 0) {
      toast({
        title: "More information needed",
        description: "Please provide a writing sample of at least 50 words or upload a document.",
        variant: "destructive",
      })
      return
    }
    
    setActiveStep((prevStep) => prevStep + 1)
  }
  
  const handleBack = () => {
    setActiveStep((prevStep) => prevStep - 1)
  }
  
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData({
      ...formData,
      [name]: value,
    })
  }
  
  const handleTopicToggle = (topic: string) => {
    setFormData(prev => {
      const isSelected = prev.preferredTopics.includes(topic)
      if (isSelected) {
        return {
          ...prev,
          preferredTopics: prev.preferredTopics.filter(t => t !== topic)
        }
      } else {
        return {
          ...prev,
          preferredTopics: [...prev.preferredTopics, topic]
        }
      }
    })
  }
  
  const handleAddCustomTopics = () => {
    const newTopics = parseTopicsFromText(formData.customTopics)
    if (newTopics.length === 0) return
    
    setFormData(prev => ({
      ...prev,
      preferredTopics: [...new Set([...prev.preferredTopics, ...newTopics])],
      customTopics: ''
    }))
  }
  
  const handleCountrySelect = (value: string) => {
    if (formData.preferredCountries.length >= 5) {
      toast({
        title: "Maximum countries reached",
        description: "You can select up to 5 countries. Remove one to add another.",
        variant: "destructive",
      })
      return
    }
    
    setFormData(prev => ({
      ...prev,
      preferredCountries: [...prev.preferredCountries, value]
    }))
  }
  
  const handleRemoveCountry = (country: string) => {
    setFormData(prev => ({
      ...prev,
      preferredCountries: prev.preferredCountries.filter(c => c !== country)
    }))
  }
  
  const handleRemoveFile = (fileToRemove: File) => {
    setFormData(prev => ({
      ...prev,
      uploadedDocuments: prev.uploadedDocuments.filter(file => file !== fileToRemove)
    }))
  }
  
  const submitOnboarding = async () => {
    try {
      setIsSubmitting(true)
      
      // First create the writing profile
      const writingProfileData = {
        writing_samples: formData.writingSample,
        preferred_topics: formData.preferredTopics,
        preferred_countries: formData.preferredCountries,
        delegate_style: formData.delegateStyle,
        past_papers: formData.pastPapers,
        past_speeches: formData.pastSpeeches,
        past_resolutions: formData.pastResolutions
      }
      
      const profileResponse = await fetch('/api/onboarding/writing-profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'user-id': userId,
        },
        body: JSON.stringify(writingProfileData),
      })
      
      if (!profileResponse.ok) {
        const error = await profileResponse.json()
        throw new Error(error.error || 'Failed to create writing profile')
      }
      
      // If we have documents to upload, process them (in a real app)
      // For now, we're just marking onboarding as complete
      const completeResponse = await fetch('/api/onboarding/complete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'user-id': userId,
        },
      })
      
      if (!completeResponse.ok) {
        const error = await completeResponse.json()
        throw new Error(error.error || 'Failed to complete onboarding')
      }
      
      // Onboarding complete
      toast({
        title: "Onboarding complete!",
        description: "Your profile has been set up and you're ready to start.",
      })
      
      onComplete()
    } catch (error) {
      console.error('Error during onboarding:', error)
      toast({
        title: "Error during onboarding",
        description: error instanceof Error ? error.message : "An unexpected error occurred",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }
  
  return (
    <div className="container mx-auto max-w-3xl py-8">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-2xl font-bold text-center">Welcome to MUN Connect</CardTitle>
          <CardDescription className="text-center">
            Let's get to know your writing style and preferences to personalize your experience
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Stepper activeStep={activeStep} orientation="vertical">
            <Step>
              <StepLabel>Your Writing Style</StepLabel>
              <StepContent>
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    We'll analyze your writing style to better tailor our AI-generated content to match your voice and tone.
                  </p>
                  
                  <div className="space-y-2">
                    <Label htmlFor="writingSample">Share a writing sample</Label>
                    <Textarea
                      id="writingSample"
                      name="writingSample"
                      value={formData.writingSample}
                      onChange={handleInputChange}
                      placeholder="Paste a sample of your writing here. This could be from a previous position paper, speech, or any formal writing sample (minimum 50 words recommended)."
                      className="min-h-[150px]"
                    />
                    <p className="text-xs text-muted-foreground">
                      Word count: {formData.writingSample.split(/\s+/).filter(Boolean).length}
                      {formData.writingSample.split(/\s+/).filter(Boolean).length < 50 && 
                        " (50+ words recommended for better analysis)"}
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>Or upload previous MUN documents</Label>
                    <div
                      {...getRootProps()}
                      className={`border-2 border-dashed rounded-md p-6 text-center cursor-pointer transition-colors
                        ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/20'}`}
                    >
                      <input {...getInputProps()} />
                      <FileUp className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                      <p className="text-sm font-medium">
                        {isDragActive ? 'Drop files here' : 'Drag & drop files or click to browse'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Accepts PDF, DOC, DOCX, TXT (max 5MB each)
                      </p>
                    </div>
                    
                    {formData.uploadedDocuments.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <Label>Uploaded files</Label>
                        <div className="space-y-2">
                          {formData.uploadedDocuments.map((file, index) => (
                            <div 
                              key={index} 
                              className="flex items-center justify-between p-2 bg-muted rounded"
                            >
                              <span className="text-sm truncate max-w-[80%]">{file.name}</span>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleRemoveFile(file)}
                              >
                                <X className="h-4 w-4" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="flex justify-end">
                    <Button onClick={handleNext}>
                      Next
                      <ChevronRight className="ml-1 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </StepContent>
            </Step>
            
            <Step>
              <StepLabel>Your Delegate Profile</StepLabel>
              <StepContent>
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    Tell us about your delegate style and experience. This helps us tailor content to match your approach.
                  </p>
                  
                  <div className="space-y-2">
                    <Label htmlFor="delegateStyle">Describe your delegate style</Label>
                    <Textarea
                      id="delegateStyle"
                      name="delegateStyle"
                      value={formData.delegateStyle}
                      onChange={handleInputChange}
                      placeholder="Describe your approach as a delegate. Are you consensus-building, assertive, detail-oriented, etc.?"
                      className="min-h-[100px]"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="pastPapers">Share excerpts from your past position papers</Label>
                    <Textarea
                      id="pastPapers"
                      name="pastPapers"
                      value={formData.pastPapers}
                      onChange={handleInputChange}
                      placeholder="Paste excerpts from your previous position papers to help us understand your style."
                      className="min-h-[100px]"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="pastSpeeches">Share examples of speeches you've given</Label>
                    <Textarea
                      id="pastSpeeches"
                      name="pastSpeeches"
                      onChange={handleInputChange}
                      value={formData.pastSpeeches}
                      placeholder="Paste examples of speeches you've delivered in committee sessions."
                      className="min-h-[100px]"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="pastResolutions">Share examples of resolutions you've worked on</Label>
                    <Textarea
                      id="pastResolutions"
                      name="pastResolutions"
                      onChange={handleInputChange}
                      value={formData.pastResolutions}
                      placeholder="Paste examples of resolution clauses or points you've contributed to committees."
                      className="min-h-[100px]"
                    />
                  </div>
                  
                  <div className="flex justify-between">
                    <Button
                      variant="outline"
                      onClick={handleBack}
                    >
                      <ChevronLeft className="mr-1 h-4 w-4" />
                      Back
                    </Button>
                    <Button onClick={handleNext}>
                      Next
                      <ChevronRight className="ml-1 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </StepContent>
            </Step>
            
            <Step>
              <StepLabel>Topics of Interest</StepLabel>
              <StepContent>
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    Select the topics you're most interested in. This helps us tailor content to your areas of focus.
                  </p>
                  
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {popularTopics.map(topic => (
                      <div key={topic} className="flex items-center space-x-2">
                        <Checkbox
                          id={`topic-${topic}`}
                          checked={formData.preferredTopics.includes(topic)}
                          onCheckedChange={() => handleTopicToggle(topic)}
                        />
                        <label
                          htmlFor={`topic-${topic}`}
                          className="text-sm cursor-pointer"
                        >
                          {topic}
                        </label>
                      </div>
                    ))}
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="customTopics">Add custom topics</Label>
                    <div className="flex space-x-2">
                      <Input
                        id="customTopics"
                        name="customTopics"
                        value={formData.customTopics}
                        onChange={handleInputChange}
                        placeholder="Enter topics separated by commas"
                      />
                      <Button
                        type="button"
                        onClick={handleAddCustomTopics}
                        disabled={!formData.customTopics.trim()}
                      >
                        Add
                      </Button>
                    </div>
                  </div>
                  
                  <div className="flex justify-between">
                    <Button
                      variant="outline"
                      onClick={handleBack}
                    >
                      <ChevronLeft className="mr-1 h-4 w-4" />
                      Back
                    </Button>
                    <Button onClick={handleNext}>
                      Next
                      <ChevronRight className="ml-1 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </StepContent>
            </Step>
            
            <Step>
              <StepLabel>Preferred Countries</StepLabel>
              <StepContent>
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    Select up to 5 countries you're interested in representing. This helps us prepare relevant content.
                  </p>
                  
                  <div className="space-y-2">
                    <Label htmlFor="countrySelect">Select countries (max 5)</Label>
                    <Select onValueChange={handleCountrySelect}>
                      <SelectTrigger id="countrySelect">
                        <SelectValue placeholder="Select a country" />
                      </SelectTrigger>
                      <SelectContent className="max-h-[300px]">
                        {countries.map(country => (
                          <SelectItem 
                            key={country} 
                            value={country}
                            disabled={formData.preferredCountries.includes(country)}
                          >
                            {country}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {formData.preferredCountries.length > 0 && (
                    <div className="space-y-2">
                      <Label>Selected countries</Label>
                      <div className="flex flex-wrap gap-2">
                        {formData.preferredCountries.map(country => (
                          <div 
                            key={country}
                            className="flex items-center space-x-1 bg-primary/10 text-primary rounded-full px-3 py-1"
                          >
                            <span className="text-sm">{country}</span>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-5 w-5 p-0 rounded-full"
                              onClick={() => handleRemoveCountry(country)}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="flex justify-between">
                    <Button
                      variant="outline"
                      onClick={handleBack}
                    >
                      <ChevronLeft className="mr-1 h-4 w-4" />
                      Back
                    </Button>
                    <Button onClick={handleNext}>
                      Next
                      <ChevronRight className="ml-1 h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </StepContent>
            </Step>
            
            <Step>
              <StepLabel>Review and Finish</StepLabel>
              <StepContent>
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    Please review your preferences. Click Finish to complete the onboarding process.
                  </p>
                  
                  <div className="space-y-3 rounded-md border p-4">
                    <div>
                      <h4 className="font-medium">Writing Sample</h4>
                      <p className="text-sm text-muted-foreground">
                        {formData.writingSample 
                          ? formData.writingSample.length > 100 
                            ? `${formData.writingSample.substring(0, 100)}...` 
                            : formData.writingSample
                          : "No writing sample provided"}
                      </p>
                    </div>
                    
                    <div>
                      <h4 className="font-medium">Delegate Style</h4>
                      <p className="text-sm text-muted-foreground">
                        {formData.delegateStyle 
                          ? formData.delegateStyle.length > 100 
                            ? `${formData.delegateStyle.substring(0, 100)}...` 
                            : formData.delegateStyle
                          : "No delegate style provided"}
                      </p>
                    </div>
                    
                    <div>
                      <h4 className="font-medium">Preferred Topics</h4>
                      <p className="text-sm text-muted-foreground">
                        {formData.preferredTopics.length > 0 
                          ? formData.preferredTopics.join(", ") 
                          : "No topics selected"}
                      </p>
                    </div>
                    
                    <div>
                      <h4 className="font-medium">Preferred Countries</h4>
                      <p className="text-sm text-muted-foreground">
                        {formData.preferredCountries.length > 0 
                          ? formData.preferredCountries.join(", ") 
                          : "No countries selected"}
                      </p>
                    </div>
                    
                    <div>
                      <h4 className="font-medium">Uploaded Documents</h4>
                      <p className="text-sm text-muted-foreground">
                        {formData.uploadedDocuments.length > 0 
                          ? formData.uploadedDocuments.map(file => file.name).join(", ") 
                          : "No documents uploaded"}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex justify-between">
                    <Button
                      variant="outline"
                      onClick={handleBack}
                    >
                      <ChevronLeft className="mr-1 h-4 w-4" />
                      Back
                    </Button>
                    <Button 
                      onClick={submitOnboarding}
                      disabled={isSubmitting}
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <CheckCircle className="mr-2 h-4 w-4" />
                          Finish
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </StepContent>
            </Step>
          </Stepper>
        </CardContent>
      </Card>
    </div>
  )
} 