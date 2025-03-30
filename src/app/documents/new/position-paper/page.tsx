"use client"

import { useState, useEffect } from "react"
import { DashboardLayout } from "@/components/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { ChevronLeft, ChevronRight, Upload, FileText, Sparkles, Save } from "lucide-react"
import { motion } from "framer-motion"
import { useToast } from "@/components/ui/use-toast"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"
import { RichTextEditor } from "@/components/rich-text-editor"
import { Toaster } from "@/components/ui/toaster"
import { createClient } from '@supabase/supabase-js'
import { ConferenceForm } from "@/components/conference-form"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { supabase } from "@/lib/supabase-client"

// Mock data
const conferences = [
  { id: 1, name: "Harvard National Model United Nations (HNMUN)" },
  { id: 2, name: "Yale Model United Nations (YMUN)" },
  { id: 3, name: "Princeton Model United Nations Conference (PMUNC)" },
]

const committees = [
  { id: 1, name: "UN Security Council" },
  { id: 2, name: "World Health Organization" },
  { id: 3, name: "UN General Assembly" },
]

const topics = [
  { id: 1, name: "Climate Change and Environmental Security" },
  { id: 2, name: "Global Health Crisis Response" },
  { id: 3, name: "Nuclear Disarmament and Non-Proliferation" },
]

const countries = [
  { id: 1, name: "France" },
  { id: 2, name: "Germany" },
  { id: 3, name: "Japan" },
]

const templates = [
  { id: 1, name: "Standard Position Paper", description: "Traditional format with introduction, body, and conclusion" },
  { id: 2, name: "Harvard Style", description: "Specific format required for Harvard MUN conferences" },
  { id: 3, name: "Detailed Analysis", description: "In-depth analysis with policy recommendations" },
]

export default function NewPositionPaper() {
  const { user, isLoading: authLoading } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  const [step, setStep] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [generatedContent, setGeneratedContent] = useState("")
  const [userConferences, setUserConferences] = useState<any[]>([])
  const [isEditorReady, setIsEditorReady] = useState(false)
  const [dataFetched, setDataFetched] = useState(false)
  const [isAddConferenceOpen, setIsAddConferenceOpen] = useState(false)
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  
  const [formData, setFormData] = useState({
    conference: "",
    committee: "",
    committee_type: "GA", // GA, SC, crisis, specialized, other
    topic: "",
    country: "",
    backgroundText: "",
    backgroundGuideUrls: [""],
    relevantSourceUrls: [""],
    positionPaperGuidelines: "",
    formattingTipsPage: "",
    template: "Standard Position Paper",
    customRequirements: "",
  })

  // Debug auth state
  useEffect(() => {
    console.log("Auth state in Position Paper:", { user, authLoading })
  }, [user, authLoading])

  // Fetch user's conferences for selection
  useEffect(() => {
    // Only proceed if authentication is done loading
    if (authLoading) return
    
    // If user is not authenticated after auth loading is complete, redirect
    if (!user && !authLoading) {
      console.log("User not authenticated, redirecting to login")
      router.push('/auth/login')
      return
    }
    
    // Skip if we've already fetched the data
    if (dataFetched) return
    
    const fetchConferences = async () => {
      try {
        console.log("Fetching conferences with user ID:", user?.id)
        
        // Get user session to ensure authentication
        const { data: sessionData } = await supabase.auth.getSession()
        
        if (!sessionData.session) {
          console.error("No active session found");
          return;
        }
        
        // Fetch ALL conferences from Supabase directly (removed status filter)
        const { data, error } = await supabase
          .from('conferences')
          .select('*')
          .eq('user_id', user?.id)
          .order('created_at', { ascending: false })
        
        if (error) {
          throw error;
        }
        
        console.log("Fetched conferences:", data);
        setUserConferences(data || [])
        setDataFetched(true)
      } catch (err) {
        console.error("Error fetching conferences:", err)
        toast({
          title: "Error loading conferences",
          description: "Unable to load your conferences. Please try again later.",
          variant: "destructive",
        })
      }
    }
    
    if (user) {
      fetchConferences()
    }
  }, [user, router, authLoading, dataFetched, toast])

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/auth/login')
    }
  }, [user, authLoading, router])

  const handleNext = () => {
    setStep(step + 1)
  }

  const handleBack = () => {
    setStep(step - 1)
  }

  const handleChange = (field: string, value: string) => {
    setFormData({
      ...formData,
      [field]: value,
    })
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData({
      ...formData,
      [name]: value,
    })
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return
    
    const file = e.target.files[0]
    setPdfFile(file)
    
    const reader = new FileReader()
    
    reader.onload = (e) => {
      if (e.target && typeof e.target.result === "string") {
        setFormData({
          ...formData,
          backgroundText: e.target.result
        })
      }
    }
    
    if (file.type === 'application/pdf') {
      toast({
        title: "PDF Added",
        description: `File "${file.name}" will be processed with your submission.`,
      })
    } else {
      reader.readAsText(file)
    }
  }

  const addBackgroundGuideUrl = () => {
    setFormData({
      ...formData,
      backgroundGuideUrls: [...formData.backgroundGuideUrls, ""]
    });
  }

  const updateBackgroundGuideUrl = (index: number, value: string) => {
    const updatedUrls = [...formData.backgroundGuideUrls];
    updatedUrls[index] = value;
    setFormData({
      ...formData,
      backgroundGuideUrls: updatedUrls
    });
  }

  const removeBackgroundGuideUrl = (index: number) => {
    if (formData.backgroundGuideUrls.length <= 1) return;
    const updatedUrls = formData.backgroundGuideUrls.filter((_, i) => i !== index);
    setFormData({
      ...formData,
      backgroundGuideUrls: updatedUrls
    });
  }

  const addRelevantSourceUrl = () => {
    setFormData({
      ...formData,
      relevantSourceUrls: [...formData.relevantSourceUrls, ""]
    });
  }

  const updateRelevantSourceUrl = (index: number, value: string) => {
    const updatedUrls = [...formData.relevantSourceUrls];
    updatedUrls[index] = value;
    setFormData({
      ...formData,
      relevantSourceUrls: updatedUrls
    });
  }

  const removeRelevantSourceUrl = (index: number) => {
    if (formData.relevantSourceUrls.length <= 1) return;
    const updatedUrls = formData.relevantSourceUrls.filter((_, i) => i !== index);
    setFormData({
      ...formData,
      relevantSourceUrls: updatedUrls
    });
  }

  const generatePositionPaper = async () => {
    if (!user || !user.id) {
      console.error("User not authenticated or missing ID:", user)
      toast({
        title: "Authentication required",
        description: "Please sign in to generate a position paper",
        variant: "destructive",
      })
      return
    }
    
    // Validate form
    if (!formData.conference || !formData.committee || !formData.topic || !formData.country) {
      toast({
        title: "Missing information",
        description: "Please fill out all required fields",
        variant: "destructive",
      })
      return
    }
    
    setIsLoading(true)
    console.log("Generating position paper with user ID:", user.id)
    
    try {
      // Create Supabase client and ensure profile exists - use shared client
      // Check if user profile exists
      const { data: profileData, error: profileError } = await supabase
        .from('profiles')
        .select('id')
        .eq('id', user.id)
        .single()
      
      // If profile doesn't exist, create it
      if (profileError) {
        console.log("Profile not found, creating profile for user:", user.id)
        const { error: createError } = await supabase
          .from('profiles')
          .insert({
            id: user.id,
            email: user.email,
            full_name: user.user_metadata?.full_name || '',
            username: user.email?.split('@')[0] || `user_${Date.now()}`,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          })
        
        if (createError) {
          console.error("Error creating profile:", createError)
          throw new Error("Failed to create user profile. Please try again or contact support.")
        }
      }
      
      // Create form data for file upload if needed
      const formDataObj = new FormData()
      if (pdfFile && pdfFile.type === 'application/pdf') {
        formDataObj.append('pdf', pdfFile)
      }
      
      // Prepare request data
      const requestData = {
        conference: formData.conference,
        committee: formData.committee,
        committee_type: formData.committee_type,
        topic: formData.topic,
        country: formData.country,
        background_text: formData.backgroundText,
        background_guide_urls: formData.backgroundGuideUrls.filter(url => url.trim()),
        relevant_source_urls: formData.relevantSourceUrls.filter(url => url.trim()),
        position_paper_guidelines: formData.positionPaperGuidelines,
        formatting_tips_page: formData.formattingTipsPage,
        template: formData.template,
        custom_requirements: formData.customRequirements,
        user_id: user.id,
      }
      
      console.log("Request data:", requestData)
      
      // Get current session
      const { data: sessionData } = await supabase.auth.getSession()
      
      if (!sessionData.session) {
        console.error("No active session found")
        throw new Error("Authentication session expired. Please log in again.")
      }
      
      const accessToken = sessionData.session.access_token
      console.log("Got access token:", accessToken ? "Yes (length: " + accessToken.length + ")" : "No")
      
      // If we have a PDF file, handle it separately with FormData
      let response;
      if (pdfFile && pdfFile.type === 'application/pdf') {
        // Add all text fields to FormData
        Object.entries(requestData).forEach(([key, value]) => {
          if (Array.isArray(value)) {
            value.forEach(item => formDataObj.append(`${key}[]`, item))
          } else {
            formDataObj.append(key, String(value))
          }
        })
        
        response = await fetch("/api/ai/generate-position-paper", {
          method: "POST",
          headers: {
            "user-id": user.id,
            "Authorization": `Bearer ${accessToken}`,
          },
          body: formDataObj,
        })
      } else {
        // Standard JSON request without file
        response = await fetch("/api/ai/generate-position-paper", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "user-id": user.id,
            "Authorization": `Bearer ${accessToken}`,
          },
          body: JSON.stringify(requestData),
        })
      }
      
      console.log("Response status:", response.status)
      
      if (!response.ok) {
        let errorMessage = "Failed to generate position paper";
        
        if (response.status === 401) {
          errorMessage = "Authentication error. Please log out and log back in.";
          toast({
            title: "Session expired",
            description: "Your session has expired. Please log out and log back in.",
            variant: "destructive",
          });
          
          // Don't auto-redirect as it might be confusing to users
          setIsLoading(false);
          return;
        }
        
        try {
          const errorData = await response.json();
          console.error("Position paper generation error:", errorData);
          errorMessage = errorData.error || errorMessage;
        } catch (parseError) {
          const text = await response.text();
          console.error("Error parsing error response:", text);
        }
        
        throw new Error(errorMessage);
      }
      
      let data;
      try {
        const text = await response.text();
        data = JSON.parse(text);
      } catch (e) {
        console.error("Error parsing success response:", e);
        throw new Error("Invalid response format from server");
      }
      
      console.log("Position paper generated successfully");
      setGeneratedContent(data.content);
      
      toast({
        title: "Position paper generated",
        description: "Your position paper has been successfully generated",
      })
      
      // Move to edit mode
      setStep(5)
    } catch (error: any) {
      console.error("Position paper generation exception:", error)
      toast({
        title: "Error generating position paper",
        description: error.message || "An unexpected error occurred",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const saveDocument = async (content: string) => {
    if (!user || !user.id) {
      console.error("User not authenticated or missing ID:", user)
      toast({
        title: "Authentication required",
        description: "Please sign in to save your document",
        variant: "destructive",
      })
      return
    }
    
    try {
      setIsLoading(true)
      console.log("Saving document with user ID:", user.id)
      
      const response = await fetch(`/api/documents/new`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "user-id": user.id,
        },
        body: JSON.stringify({
          title: `${formData.country} - ${formData.topic}`,
          type: "Position Paper",
          committee: formData.committee,
          conference: formData.conference,
          content: content,
          progress: 100,
          user_id: user.id, // Include in body as fallback
        }),
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error("Document save error:", errorData)
        throw new Error(errorData.error || "Failed to save document")
      }
      
      toast({
        title: "Document saved",
        description: "Your position paper has been saved successfully",
      })
      
      // Redirect to the documents page
      router.push('/documents')
    } catch (error: any) {
      console.error("Document save exception:", error)
      toast({
        title: "Error saving document",
        description: error.message || "An unexpected error occurred",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  // Handler for conference form success
  const handleConferenceAdded = (conferenceId?: number, conferenceName?: string) => {
    setIsAddConferenceOpen(false)
    
    // Set the newly created conference in the form
    if (conferenceName) {
      setFormData({
        ...formData,
        conference: conferenceName
      })
    }
    
    // Refetch conferences to include the new one
    setDataFetched(false)
    
    toast({
      title: "Conference added",
      description: "Your new conference has been added and selected",
    })
  }

  // Show loading state while authentication is being checked
  if (authLoading) {
    return (
      <DashboardLayout>
        <div className="container mx-auto max-w-4xl py-6">
          <div className="flex flex-col items-center justify-center h-96">
            <p className="text-muted-foreground">Loading...</p>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  // Don't render main content if user is not authenticated
  if (!user) {
    return null // Will redirect in useEffect
  }

  // Render the appropriate step content
  const renderStepContent = () => {
    const fadeIn = {
      hidden: { opacity: 0, y: 20 },
      visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
    };

    switch (step) {
      case 1:
        return (
          <motion.div
            key="step1"
            initial="hidden"
            animate="visible"
            variants={fadeIn}
            className="space-y-6"
          >
            <div className="space-y-1">
              <h2 className="text-2xl font-bold">Conference & Committee Details</h2>
              <p className="text-muted-foreground">
                Let's start with basic information about your MUN conference
              </p>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label htmlFor="conference">Conference *</Label>
                  <Button 
                    type="button" 
                    variant="outline" 
                    size="sm"
                    onClick={() => setIsAddConferenceOpen(true)}
                  >
                    + Add New
                  </Button>
                </div>
                <Select
                  value={formData.conference}
                  onValueChange={(value) => handleChange("conference", value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a conference" />
                  </SelectTrigger>
                  <SelectContent>
                    {userConferences.length > 0 ? (
                      userConferences.map((conf) => (
                        <SelectItem key={conf.id} value={conf.name}>
                          {conf.name}
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="add-new" disabled>
                        No conferences found (click "Add New" above)
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="committee">Committee Name *</Label>
                <Input
                  id="committee"
                  name="committee"
                  placeholder="UN Security Council"
                  value={formData.committee}
                  onChange={handleInputChange}
                />
              </div>
              
              <div className="space-y-2">
                <Label>Committee Type</Label>
                <Select
                  value={formData.committee_type}
                  onValueChange={(value) => handleChange("committee_type", value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select committee type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="GA">General Assembly</SelectItem>
                    <SelectItem value="SC">Security Council</SelectItem>
                    <SelectItem value="crisis">Crisis Committee</SelectItem>
                    <SelectItem value="specialized">Specialized Agency</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="topic">Committee Topic *</Label>
                <Input
                  id="topic"
                  name="topic"
                  placeholder="Climate Change and Environmental Security"
                  value={formData.topic}
                  onChange={handleInputChange}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="country">Country/Character *</Label>
                <Input
                  id="country"
                  name="country"
                  placeholder="France"
                  value={formData.country}
                  onChange={handleInputChange}
                />
              </div>
            </div>
          </motion.div>
        );
      
      case 2:
        return (
          <motion.div
            key="step2"
            initial="hidden"
            animate="visible"
            variants={fadeIn}
            className="space-y-6"
          >
            <div className="space-y-1">
              <h2 className="text-2xl font-bold">Background Information</h2>
              <p className="text-muted-foreground">
                Add background guides and relevant research sources
              </p>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="backgroundText">Background Text</Label>
                <Textarea
                  id="backgroundText"
                  name="backgroundText"
                  placeholder="Paste background information or research notes here..."
                  value={formData.backgroundText}
                  onChange={handleInputChange}
                  rows={6}
                  className="min-h-[150px]"
                />
                <div className="text-xs text-muted-foreground">
                  Paste text from research or background guides to help generate a more informed position paper
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="fileUpload">Upload Background File (PDF or TXT)</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="fileUpload"
                    type="file"
                    accept=".txt,.pdf"
                    onChange={handleFileUpload}
                    className="flex-1"
                  />
                  {pdfFile && (
                    <div className="text-sm text-muted-foreground flex items-center gap-1">
                      <FileText className="h-4 w-4" />
                      {pdfFile.name}
                    </div>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  Upload a PDF or text file containing background information
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Background Guide URLs</Label>
                <div className="space-y-2">
                  {formData.backgroundGuideUrls.map((url, index) => (
                    <div key={`bg-${index}`} className="flex items-center gap-2">
                      <Input
                        placeholder="https://example.com/background-guide.pdf"
                        value={url}
                        onChange={(e) => updateBackgroundGuideUrl(index, e.target.value)}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        onClick={() => removeBackgroundGuideUrl(index)}
                        disabled={formData.backgroundGuideUrls.length <= 1}
                      >
                        <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                          -
                        </motion.div>
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    onClick={addBackgroundGuideUrl}
                    className="w-full"
                  >
                    <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                      Add Another Background Guide URL
                    </motion.div>
                  </Button>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Relevant Source URLs</Label>
                <div className="space-y-2">
                  {formData.relevantSourceUrls.map((url, index) => (
                    <div key={`src-${index}`} className="flex items-center gap-2">
                      <Input
                        placeholder="https://example.com/relevant-source.html"
                        value={url}
                        onChange={(e) => updateRelevantSourceUrl(index, e.target.value)}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        onClick={() => removeRelevantSourceUrl(index)}
                        disabled={formData.relevantSourceUrls.length <= 1}
                      >
                        <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                          -
                        </motion.div>
                      </Button>
                    </div>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    onClick={addRelevantSourceUrl}
                    className="w-full"
                  >
                    <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                      Add Another Source URL
                    </motion.div>
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        );
      
      case 3:
        return (
          <motion.div
            key="step3"
            initial="hidden"
            animate="visible"
            variants={fadeIn}
            className="space-y-6"
          >
            <div className="space-y-1">
              <h2 className="text-2xl font-bold">Formatting Guidelines</h2>
              <p className="text-muted-foreground">
                Specify position paper guidelines and formatting requirements
              </p>
            </div>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="positionPaperGuidelines">Position Paper Guidelines</Label>
                <Textarea
                  id="positionPaperGuidelines"
                  name="positionPaperGuidelines"
                  placeholder="Enter any specific guidelines provided by the conference..."
                  value={formData.positionPaperGuidelines}
                  onChange={handleInputChange}
                  rows={4}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="formattingTipsPage">Formatting Tips Page Reference</Label>
                <Input
                  id="formattingTipsPage"
                  name="formattingTipsPage"
                  placeholder="e.g., 'Page 5 of the background guide'"
                  value={formData.formattingTipsPage}
                  onChange={handleInputChange}
                />
                <div className="text-xs text-muted-foreground">
                  Reference to where formatting guidelines can be found in the background guide
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="template">Paper Template</Label>
                <Select
                  value={formData.template}
                  onValueChange={(value) => handleChange("template", value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a template" />
                  </SelectTrigger>
                  <SelectContent>
                    {templates.map((template) => (
                      <SelectItem key={template.id} value={template.name}>
                        {template.name} - {template.description}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="customRequirements">Custom Requirements</Label>
                <Textarea
                  id="customRequirements"
                  name="customRequirements"
                  placeholder="Any additional formatting or content requirements..."
                  value={formData.customRequirements}
                  onChange={handleInputChange}
                  rows={4}
                />
              </div>
            </div>
          </motion.div>
        );
      
      case 4:
        return (
          <motion.div
            key="step4"
            initial="hidden"
            animate="visible"
            variants={fadeIn}
            className="space-y-6"
          >
            <div className="space-y-1">
              <h2 className="text-2xl font-bold">Review & Generate</h2>
              <p className="text-muted-foreground">
                Review your information and generate your position paper
              </p>
            </div>
            
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Conference & Committee</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="text-sm font-medium">Conference:</div>
                    <div className="text-sm">{formData.conference}</div>
                    <div className="text-sm font-medium">Committee:</div>
                    <div className="text-sm">{formData.committee}</div>
                    <div className="text-sm font-medium">Committee Type:</div>
                    <div className="text-sm">{formData.committee_type}</div>
                    <div className="text-sm font-medium">Topic:</div>
                    <div className="text-sm">{formData.topic}</div>
                    <div className="text-sm font-medium">Country/Character:</div>
                    <div className="text-sm">{formData.country}</div>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle>Research Sources</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="text-sm font-medium">Background Guides:</div>
                  <div className="text-sm">
                    {formData.backgroundGuideUrls.filter(url => url.trim()).length > 0 ? (
                      <ul className="list-disc list-inside">
                        {formData.backgroundGuideUrls.filter(url => url.trim()).map((url, index) => (
                          <li key={`bg-review-${index}`}>{url}</li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-muted-foreground">No background guides provided</span>
                    )}
                  </div>
                  
                  <div className="text-sm font-medium mt-2">Relevant Sources:</div>
                  <div className="text-sm">
                    {formData.relevantSourceUrls.filter(url => url.trim()).length > 0 ? (
                      <ul className="list-disc list-inside">
                        {formData.relevantSourceUrls.filter(url => url.trim()).map((url, index) => (
                          <li key={`src-review-${index}`}>{url}</li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-muted-foreground">No sources provided</span>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </motion.div>
        );
      
      case 5:
        return (
          <motion.div
            key="step5"
            initial="hidden"
            animate="visible"
            variants={fadeIn}
            className="space-y-6"
          >
            <div className="space-y-1">
              <h2 className="text-2xl font-bold">Edit Your Position Paper</h2>
              <p className="text-muted-foreground">
                Review and edit the generated position paper
              </p>
            </div>
            
            <RichTextEditor
              initialValue={generatedContent}
              onChange={(content) => setGeneratedContent(content)}
              className="min-h-[500px] border rounded-md"
            />
          </motion.div>
        );
      
      default:
        return null;
    }
  };

  return (
    <DashboardLayout>
      <div className="container max-w-5xl py-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Create Position Paper</h1>
            <p className="text-muted-foreground">
              Create a professional position paper for your Model UN conference
            </p>
          </div>
        </div>
        
        <Card>
          <CardContent className="p-6">
            <div className="mb-8">
              <div className="flex justify-between items-center mb-2">
                <div className="text-sm font-medium">Step {step} of 5</div>
                <div className="text-sm text-muted-foreground">
                  {step === 1 && "Conference & Committee"}
                  {step === 2 && "Background Information"}
                  {step === 3 && "Formatting Guidelines"}
                  {step === 4 && "Review & Generate"}
                  {step === 5 && "Edit Paper"}
                </div>
              </div>
              <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-primary"
                  initial={{ width: `${(step - 1) * 20}%` }}
                  animate={{ width: `${step * 20}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
            
            {renderStepContent()}
            
            <div className="flex justify-between mt-8">
              <Button
                type="button"
                variant="outline"
                onClick={handleBack}
                disabled={step === 1 || isLoading}
              >
                <ChevronLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              
              {step < 4 ? (
                <Button type="button" onClick={handleNext} disabled={isLoading}>
                  Next <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              ) : step === 4 ? (
                <Button 
                  type="button" 
                  onClick={generatePositionPaper}
                  disabled={isLoading}
                  className="gap-2"
                >
                  {isLoading ? (
                    <>Generating...</>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" /> Generate Position Paper
                    </>
                  )}
                </Button>
              ) : (
                <Button 
                  type="button" 
                  onClick={() => saveDocument(generatedContent)}
                  disabled={isLoading || !isEditorReady}
                  className="gap-2"
                >
                  {isLoading ? (
                    <>Saving...</>
                  ) : (
                    <>
                      <Save className="h-4 w-4" /> Save Document
                    </>
                  )}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Add Conference Dialog */}
        <Dialog open={isAddConferenceOpen} onOpenChange={setIsAddConferenceOpen}>
          <DialogContent className="sm:max-w-[500px] p-0">
            <DialogTitle className="sr-only">Add New Conference</DialogTitle>
            <ConferenceForm 
              onSuccess={handleConferenceAdded} 
              onCancel={() => setIsAddConferenceOpen(false)} 
            />
          </DialogContent>
        </Dialog>
      </div>
      <Toaster />
    </DashboardLayout>
  );
}

