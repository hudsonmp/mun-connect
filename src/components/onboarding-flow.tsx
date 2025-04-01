"use client"

import React, { useState, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useToast } from '@/components/ui/use-toast'
import { Loader2, Upload, FileUp, ChevronRight, ChevronLeft, CheckCircle } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { 
  Stepper,
  Step,
  StepLabel,
  StepContent,
  StepConnector,
} from '@/components/ui/stepper'
import countries from '@/lib/countries'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'

const popularTopics = [
  "Climate Change", "Refugee Crisis", "Nuclear Disarmament", "Global Health",
  "Human Rights", "Economic Development", "Food Security", "Cybersecurity",
  "Terrorism", "Peace and Security", "Women's Rights", "Children's Rights",
  "Water Security", "Technology Access", "Education", "Poverty Reduction"
]

const parseTopicsFromText = (text: string): string[] => {
  if (!text.trim()) return []
  
  return text
    .split(',')
    .map(topic => topic.trim())
    .filter(topic => topic.length > 0)
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
  })
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()
  const router = useRouter()
  
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
  
  const handleCountrySelect = (country: string) => {
    setFormData(prev => {
      const isSelected = prev.preferredCountries.includes(country)
      if (isSelected) {
        return {
          ...prev,
          preferredCountries: prev.preferredCountries.filter(c => c !== country)
        }
      } else {
        // Limit to 5 countries
        if (prev.preferredCountries.length >= 5) {
          toast({
            title: "Maximum countries reached",
            description: "You can select up to 5 countries. Remove one before adding another.",
          })
          return prev
        }
        return {
          ...prev,
          preferredCountries: [...prev.preferredCountries, country]
        }
      }
    })
  }
  
  const handleFileUpload = useCallback((acceptedFiles: File[]) => {
    // Validate file types (allow only document formats)
    const validFiles = acceptedFiles.filter(file => 
      file.type === 'application/pdf' ||
      file.type === 'application/msword' ||
      file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
      file.type === 'text/plain'
    )
    
    if (validFiles.length !== acceptedFiles.length) {
      toast({
        title: "Invalid file type",
        description: "Only PDF, DOC, DOCX, and TXT files are allowed.",
        variant: "destructive",
      })
    }
    
    // Check file sizes (max 5MB)
    const validSizeFiles = validFiles.filter(file => file.size <= 5 * 1024 * 1024)
    
    if (validSizeFiles.length !== validFiles.length) {
      toast({
        title: "File too large",
        description: "Maximum file size is 5MB.",
        variant: "destructive",
      })
    }
    
    if (validSizeFiles.length > 0) {
      setFormData(prev => ({
        ...prev,
        uploadedDocuments: [...prev.uploadedDocuments, ...validSizeFiles]
      }))
      
      toast({
        title: "Files uploaded",
        description: `${validSizeFiles.length} file(s) successfully uploaded.`,
      })
    }
  }, [toast])
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleFileUpload,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 3,
  })
  
  const removeFile = (index: number) => {
    setFormData(prev => ({
      ...prev,
      uploadedDocuments: prev.uploadedDocuments.filter((_, i) => i !== index)
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
                        <Label>Uploaded documents</Label>
                        <div className="space-y-2">
                          {formData.uploadedDocuments.map((file, index) => (
                            <div key={index} className="flex items-center justify-between p-2 bg-muted rounded-md">
                              <div className="flex items-center space-x-2">
                                <Upload className="h-4 w-4 text-muted-foreground" />
                                <span className="text-sm truncate max-w-[250px]">{file.name}</span>
                              </div>
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                onClick={() => removeFile(index)}
                              >
                                Remove
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
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
                  
                  {formData.preferredTopics.length > 0 && (
                    <div className="space-y-2">
                      <Label>Selected topics</Label>
                      <div className="flex flex-wrap gap-2">
                        {formData.preferredTopics.map(topic => (
                          <Badge 
                            key={topic} 
                            variant="secondary"
                            className="cursor-pointer"
                            onClick={() => handleTopicToggle(topic)}
                          >
                            {topic} &times;
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
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
                      <SelectTrigger>
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
                          <Badge 
                            key={country} 
                            variant="secondary"
                            className="cursor-pointer"
                            onClick={() => handleCountrySelect(country)}
                          >
                            {country} &times;
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </StepContent>
            </Step>
            
            <Step>
              <StepLabel>Complete Setup</StepLabel>
              <StepContent>
                <div className="space-y-4">
                  <div className="rounded-lg border p-4 space-y-3">
                    <div>
                      <h4 className="font-medium">Writing Sample</h4>
                      <p className="text-sm text-muted-foreground">
                        {formData.writingSample
                          ? `${formData.writingSample.substring(0, 100)}${formData.writingSample.length > 100 ? '...' : ''}`
                          : 'No writing sample provided'}
                      </p>
                      {formData.uploadedDocuments.length > 0 && (
                        <p className="text-sm mt-1">
                          + {formData.uploadedDocuments.length} document(s) uploaded
                        </p>
                      )}
                    </div>
                    
                    <div>
                      <h4 className="font-medium">Topics of Interest</h4>
                      {formData.preferredTopics.length > 0 ? (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {formData.preferredTopics.map(topic => (
                            <Badge key={topic} variant="outline" className="text-xs">
                              {topic}
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">No topics selected</p>
                      )}
                    </div>
                    
                    <div>
                      <h4 className="font-medium">Preferred Countries</h4>
                      {formData.preferredCountries.length > 0 ? (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {formData.preferredCountries.map(country => (
                            <Badge key={country} variant="outline" className="text-xs">
                              {country}
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">No countries selected</p>
                      )}
                    </div>
                  </div>
                  
                  <p className="text-sm">
                    Review your information above and click Finish to complete setup. You can update these preferences later.
                  </p>
                </div>
              </StepContent>
            </Step>
          </Stepper>
        </CardContent>
        
        <CardFooter className="flex justify-between">
          <Button
            variant="outline"
            onClick={handleBack}
            disabled={activeStep === 0 || isSubmitting}
          >
            <ChevronLeft className="mr-1 h-4 w-4" />
            Back
          </Button>
          
          {activeStep === 3 ? (
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
          ) : (
            <Button onClick={handleNext}>
              Next
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  )
} 