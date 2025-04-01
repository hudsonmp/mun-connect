"use client"

import React, { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { 
  Card, 
  CardContent, 
  CardFooter, 
  CardHeader, 
  CardTitle, 
  CardDescription 
} from '@/components/ui/card'
import { 
  Form, 
  FormControl, 
  FormField, 
  FormItem, 
  FormLabel, 
  FormMessage 
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { 
  Select, 
  SelectContent, 
  SelectGroup, 
  SelectItem, 
  SelectLabel, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { useToast } from '@/components/ui/use-toast'
import { Loader2, Upload, FileUp, ChevronRight, ChevronLeft, FileText, Search, Sparkles } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import * as z from 'zod'
import { Badge } from '@/components/ui/badge'
import countries from '@/lib/countries'
import committees from '@/lib/committees'
import { MindMap } from '@/components/mind-map'

export interface DocumentCreationFlowProps {
  userId: string
  onComplete: (documentId: string) => void
  onCancel: () => void
}

// Define form validation schema
const documentFormSchema = z.object({
  document_type: z.enum(['position_paper', 'resolution', 'speech'], {
    required_error: "Please select a document type",
  }),
  committee: z.string().min(1, {
    message: "Committee is required",
  }),
  country: z.string().min(1, {
    message: "Country is required",
  }),
  topic: z.string().min(1, {
    message: "Topic is required",
  }),
  additional_context: z.string().optional(),
});

export function DocumentCreationFlow({ userId, onComplete, onCancel }: DocumentCreationFlowProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [formattingGuidelines, setFormattingGuidelines] = useState<string | null>(null)
  const [mindMapData, setMindMapData] = useState<any>(null)
  const [backgroundGuideUploaded, setBackgroundGuideUploaded] = useState(false)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()
  const router = useRouter()
  
  // Initialize form
  const form = useForm<z.infer<typeof documentFormSchema>>({
    resolver: zodResolver(documentFormSchema),
    defaultValues: {
      document_type: 'position_paper',
      committee: '',
      country: '',
      topic: '',
      additional_context: '',
    },
  })
  
  // Initialize document creation session
  useEffect(() => {
    const initSession = async () => {
      try {
        const documentType = form.getValues('document_type')
        
        const response = await fetch('/api/document-sessions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'user-id': userId,
          },
          body: JSON.stringify({
            document_type: documentType,
          }),
        })
        
        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.error || 'Failed to initialize document session')
        }
        
        const data = await response.json()
        setSessionId(data.session?.id)
      } catch (error) {
        console.error('Error creating document session:', error)
        toast({
          title: "Error",
          description: error instanceof Error ? error.message : "Failed to initialize document creation",
          variant: "destructive",
        })
      }
    }
    
    initSession()
  }, [userId, toast, form])
  
  const handleNext = async () => {
    if (currentStep === 0) {
      const result = await form.trigger(['document_type', 'committee', 'country'])
      if (!result) return
      
      // Update session with basic info
      if (sessionId) {
        try {
          await fetch(`/api/document-sessions/${sessionId}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'user-id': userId,
            },
            body: JSON.stringify({
              document_type: form.getValues('document_type'),
              committee: form.getValues('committee'),
              country: form.getValues('country'),
            }),
          })
        } catch (error) {
          console.error('Error updating session:', error)
        }
      }
    } else if (currentStep === 1) {
      const result = await form.trigger('topic')
      if (!result) return
      
      // Analyze topic if we have a background guide
      if (backgroundGuideUploaded && sessionId) {
        setIsAnalyzing(true)
        
        try {
          const response = await fetch(`/api/document-sessions/${sessionId}/analyze-topic`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'user-id': userId,
            },
            body: JSON.stringify({
              topic: form.getValues('topic'),
            }),
          })
          
          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.error || 'Failed to analyze topic')
          }
          
          const data = await response.json()
          
          if (data.mind_map) {
            setMindMapData(data.mind_map)
            toast({
              title: "Topic analyzed",
              description: "Your topic has been analyzed and a mind map has been generated",
            })
          }
        } catch (error) {
          console.error('Error analyzing topic:', error)
          toast({
            title: "Analysis error",
            description: error instanceof Error ? error.message : "Failed to analyze topic",
            variant: "destructive",
          })
        } finally {
          setIsAnalyzing(false)
        }
      }
      
      // Update session with topic
      if (sessionId) {
        try {
          await fetch(`/api/document-sessions/${sessionId}`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'user-id': userId,
            },
            body: JSON.stringify({
              topic: form.getValues('topic'),
            }),
          })
        } catch (error) {
          console.error('Error updating session:', error)
        }
      }
    }
    
    setCurrentStep(prev => prev + 1)
  }
  
  const handleBack = () => {
    setCurrentStep(prev => prev - 1)
  }
  
  const handleFileUpload = async (acceptedFiles: File[]) => {
    if (!sessionId) {
      toast({
        title: "Error",
        description: "Document session not initialized. Please try again.",
        variant: "destructive",
      })
      return
    }
    
    // Only accept the first file
    if (acceptedFiles.length === 0) return
    const file = acceptedFiles[0]
    
    // Validate file type
    const validTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
    if (!validTypes.includes(file.type)) {
      toast({
        title: "Invalid file type",
        description: "Please upload a PDF, DOC, DOCX, or TXT file.",
        variant: "destructive",
      })
      return
    }
    
    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: "File too large",
        description: "Maximum file size is 5MB.",
        variant: "destructive",
      })
      return
    }
    
    // Upload and process the file
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const response = await fetch(`/api/document-sessions/${sessionId}/upload-background`, {
        method: 'POST',
        headers: {
          'user-id': userId,
          // Don't set Content-Type for FormData
        },
        body: formData,
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to upload background guide')
      }
      
      const data = await response.json()
      
      setBackgroundGuideUploaded(true)
      if (data.formatting_guidelines) {
        setFormattingGuidelines(data.formatting_guidelines)
      }
      
      toast({
        title: "Background guide uploaded",
        description: `Successfully processed ${file.name}`,
      })
    } catch (error) {
      console.error('Error uploading background guide:', error)
      toast({
        title: "Upload error",
        description: error instanceof Error ? error.message : "Failed to upload background guide",
        variant: "destructive",
      })
    }
  }
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleFileUpload,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
  })
  
  const handleSubmit = async () => {
    if (!sessionId) {
      toast({
        title: "Error",
        description: "Document session not initialized. Please try again.",
        variant: "destructive",
      })
      return
    }
    
    try {
      setIsSubmitting(true)
      
      // Update additional context if provided
      if (form.getValues('additional_context')) {
        await fetch(`/api/document-sessions/${sessionId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'user-id': userId,
          },
          body: JSON.stringify({
            additional_context: form.getValues('additional_context'),
          }),
        })
      }
      
      // Generate the document
      const response = await fetch(`/api/document-sessions/${sessionId}/generate-document`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'user-id': userId,
        },
        body: JSON.stringify({
          additional_context: form.getValues('additional_context') || '',
        }),
      })
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to generate document')
      }
      
      const data = await response.json()
      
      toast({
        title: "Document generated",
        description: "Your document has been successfully created",
      })
      
      // Complete the flow
      if (data.document_id) {
        onComplete(data.document_id)
      } else {
        throw new Error("No document ID returned from generation")
      }
    } catch (error) {
      console.error('Error generating document:', error)
      toast({
        title: "Generation error",
        description: error instanceof Error ? error.message : "Failed to generate document",
        variant: "destructive",
      })
    } finally {
      setIsSubmitting(false)
    }
  }
  
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold">Document Information</h2>
            <p className="text-muted-foreground">
              Let's start by gathering basic information about the document you want to create.
            </p>
            
            <Form {...form}>
              <form className="space-y-4">
                <FormField
                  control={form.control}
                  name="document_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Document Type</FormLabel>
                      <FormControl>
                        <Tabs 
                          value={field.value} 
                          onValueChange={field.onChange}
                          defaultValue="position_paper"
                          className="w-full"
                        >
                          <TabsList className="grid grid-cols-3 w-full">
                            <TabsTrigger value="position_paper">Position Paper</TabsTrigger>
                            <TabsTrigger value="resolution">Resolution</TabsTrigger>
                            <TabsTrigger value="speech">Speech</TabsTrigger>
                          </TabsList>
                          <TabsContent value="position_paper" className="mt-3 text-sm text-muted-foreground">
                            A detailed paper presenting your country's stance on an issue.
                          </TabsContent>
                          <TabsContent value="resolution" className="mt-3 text-sm text-muted-foreground">
                            Formal document proposing solutions to address an issue.
                          </TabsContent>
                          <TabsContent value="speech" className="mt-3 text-sm text-muted-foreground">
                            Formal address to a committee explaining your country's position.
                          </TabsContent>
                        </Tabs>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="committee"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Committee</FormLabel>
                      <FormControl>
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select a committee" />
                          </SelectTrigger>
                          <SelectContent className="max-h-[300px]">
                            <SelectGroup>
                              <SelectLabel>General Assemblies</SelectLabel>
                              {committees.generalAssemblies.map((committee) => (
                                <SelectItem key={committee} value={committee}>
                                  {committee}
                                </SelectItem>
                              ))}
                            </SelectGroup>
                            <SelectGroup>
                              <SelectLabel>ECOSOC Committees</SelectLabel>
                              {committees.ecosoc.map((committee) => (
                                <SelectItem key={committee} value={committee}>
                                  {committee}
                                </SelectItem>
                              ))}
                            </SelectGroup>
                            <SelectGroup>
                              <SelectLabel>Specialized Agencies</SelectLabel>
                              {committees.specializedAgencies.map((committee) => (
                                <SelectItem key={committee} value={committee}>
                                  {committee}
                                </SelectItem>
                              ))}
                            </SelectGroup>
                            <SelectGroup>
                              <SelectLabel>Crisis Committees</SelectLabel>
                              {committees.crisisCommittees.map((committee) => (
                                <SelectItem key={committee} value={committee}>
                                  {committee}
                                </SelectItem>
                              ))}
                            </SelectGroup>
                          </SelectContent>
                        </Select>
                      </FormControl>
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
                      <FormControl>
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select a country" />
                          </SelectTrigger>
                          <SelectContent className="max-h-[300px]">
                            {countries.map((country) => (
                              <SelectItem key={country} value={country}>
                                {country}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </form>
            </Form>
          </div>
        );
      
      case 1:
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold">Topic & Background Guide</h2>
            <p className="text-muted-foreground">
              Now, specify the topic you're addressing and upload any background guide or reference materials.
            </p>
            
            <Form {...form}>
              <form className="space-y-4">
                <FormField
                  control={form.control}
                  name="topic"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Topic</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="e.g., Climate Change Mitigation"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <div className="space-y-2">
                  <FormLabel>Upload Background Guide (Optional)</FormLabel>
                  <div
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded-md p-6 text-center cursor-pointer transition-colors
                      ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/20'}`}
                  >
                    <input {...getInputProps()} />
                    <FileUp className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                    <p className="text-sm font-medium">
                      {isDragActive ? 'Drop file here' : 'Drag & drop file or click to browse'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Accepts PDF, DOC, DOCX, TXT (max 5MB)
                    </p>
                  </div>
                  
                  {backgroundGuideUploaded && (
                    <div className="mt-4">
                      <Badge variant="outline" className="bg-green-50 text-green-600 border-green-200">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Background guide uploaded
                      </Badge>
                      
                      {formattingGuidelines && (
                        <div className="mt-3 p-3 bg-muted rounded-md text-sm">
                          <p className="font-medium mb-1">Formatting Guidelines Found:</p>
                          <p className="text-muted-foreground">{formattingGuidelines}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </form>
            </Form>
          </div>
        );
      
      case 2:
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold">Topic Analysis & Additional Context</h2>
            <p className="text-muted-foreground">
              Review the topic analysis and provide any additional context or specific requirements.
            </p>
            
            {isAnalyzing ? (
              <div className="py-8 text-center">
                <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary mb-4" />
                <p>Analyzing your topic based on the background guide...</p>
              </div>
            ) : (
              <>
                {mindMapData ? (
                  <div className="border rounded-md p-4">
                    <h3 className="text-md font-medium mb-3">Topic Analysis</h3>
                    <MindMap data={mindMapData} />
                  </div>
                ) : (
                  <div className="border rounded-md p-6 text-center">
                    <Search className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                    <h3 className="text-md font-medium">No Topic Analysis Available</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      {backgroundGuideUploaded 
                        ? "Topic analysis could not be performed."
                        : "Upload a background guide to generate topic analysis."}
                    </p>
                  </div>
                )}
                
                <Form {...form}>
                  <form className="space-y-4">
                    <FormField
                      control={form.control}
                      name="additional_context"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Additional Context (Optional)</FormLabel>
                          <FormControl>
                            <Textarea
                              placeholder="Provide any additional context, specific requirements, or information you'd like included in your document."
                              className="min-h-[100px]"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </form>
                </Form>
              </>
            )}
          </div>
        );
      
      case 3:
        return (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold">Review & Generate</h2>
            <p className="text-muted-foreground">
              Review your document details before generating.
            </p>
            
            <div className="border rounded-md p-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Document Type</h3>
                  <p>{form.getValues('document_type').replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Committee</h3>
                  <p>{form.getValues('committee')}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Country</h3>
                  <p>{form.getValues('country')}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Topic</h3>
                  <p>{form.getValues('topic')}</p>
                </div>
              </div>
              
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Additional Information</h3>
                <ul className="list-disc pl-5 text-sm mt-1 space-y-1">
                  {backgroundGuideUploaded && <li>Background guide processed</li>}
                  {formattingGuidelines && <li>Formatting guidelines extracted</li>}
                  {mindMapData && <li>Topic analysis generated</li>}
                  {form.getValues('additional_context') && <li>Additional context provided</li>}
                </ul>
              </div>
            </div>
            
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-md p-4 flex items-start space-x-3">
              <Sparkles className="h-5 w-5 text-blue-500 mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="font-medium text-blue-700 dark:text-blue-300">What happens next?</h3>
                <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
                  Our AI will research your topic, analyze your country's position, and generate a high-quality document
                  tailored to your writing style and preferences. This may take up to 45 seconds.
                </p>
              </div>
            </div>
          </div>
        );
      
      default:
        return null;
    }
  };
  
  return (
    <div className="container mx-auto max-w-3xl py-8">
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Create New Document</CardTitle>
          <CardDescription>
            Follow the steps to generate a high-quality document tailored to your needs
          </CardDescription>
        </CardHeader>
        <CardContent>
          {renderStepContent()}
        </CardContent>
        <CardFooter className="flex justify-between">
          {currentStep > 0 ? (
            <Button 
              variant="outline" 
              onClick={handleBack}
              disabled={isSubmitting || isAnalyzing}
            >
              <ChevronLeft className="mr-1 h-4 w-4" />
              Back
            </Button>
          ) : (
            <Button
              variant="outline"
              onClick={onCancel}
              disabled={isSubmitting || isAnalyzing}
            >
              Cancel
            </Button>
          )}
          
          {currentStep < 3 ? (
            <Button 
              onClick={handleNext}
              disabled={isSubmitting || isAnalyzing}
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  Next
                  <ChevronRight className="ml-1 h-4 w-4" />
                </>
              )}
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className="bg-primary hover:bg-primary/90"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  Generate Document
                  <FileText className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  )
} 