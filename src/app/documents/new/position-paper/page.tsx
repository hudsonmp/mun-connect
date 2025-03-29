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
  
  const [formData, setFormData] = useState({
    conference: "",
    committee: "",
    topic: "",
    country: "",
    backgroundText: "",
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
    
    const fetchConferences = async () => {
      try {
        console.log("Fetching conferences with user ID:", user?.id)
        const response = await fetch(`/api/conferences?userId=${user?.id}`)
        if (response.ok) {
          const data = await response.json()
          setUserConferences(data || [])
        } else {
          const errorData = await response.json()
          console.error("Error fetching conferences:", errorData)
        }
      } catch (err) {
        console.error("Exception fetching conferences:", err)
      }
    }
    
    if (user) {
      fetchConferences()
    }
  }, [user, router, authLoading])

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
    const reader = new FileReader()
    
    reader.onload = (e) => {
      if (e.target && typeof e.target.result === "string") {
        setFormData({
          ...formData,
          backgroundText: e.target.result
        })
      }
    }
    
    reader.readAsText(file)
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
      const requestData = {
        conference: formData.conference,
        committee: formData.committee,
        topic: formData.topic,
        country: formData.country,
        background_text: formData.backgroundText,
        template: formData.template,
        custom_requirements: formData.customRequirements,
        user_id: user.id, // Include in body as fallback
      }
      
      console.log("Request data:", requestData)
      
      const response = await fetch("/api/ai/generate-position-paper", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "user-id": user.id,
        },
        body: JSON.stringify(requestData),
      })
      
      console.log("Response status:", response.status)
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error("Position paper generation error:", errorData)
        throw new Error(errorData.error || "Failed to generate position paper")
      }
      
      const data = await response.json()
      console.log("Position paper generated successfully")
      setGeneratedContent(data.content)
      
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

  return (
    <DashboardLayout>
      <div className="container mx-auto max-w-4xl py-6">
        <div className="mb-6">
          <Button variant="ghost" size="sm" onClick={() => window.history.back()}>
            <ChevronLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
          <h1 className="text-3xl font-bold mt-4">Create Position Paper</h1>
          <p className="text-muted-foreground mt-1">Generate a position paper for your MUN conference</p>
        </div>

        {step < 5 && (
          <div className="relative mb-8">
            <div className="absolute left-0 top-1/2 h-0.5 w-full -translate-y-1/2 bg-muted"></div>
            <ol className="relative z-10 flex justify-between">
              {[1, 2, 3, 4].map((i) => (
                <li key={i} className="flex items-center justify-center">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-full border-2 ${
                      step >= i ? "border-primary bg-primary text-primary-foreground" : "border-muted bg-background"
                    }`}
                  >
                    {i}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}

        {step === 1 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>Conference Details</CardTitle>
                <CardDescription>Enter the conference, committee, topic, and your country/character</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="conference">Conference *</Label>
                  {userConferences.length > 0 ? (
                    <Select value={formData.conference} onValueChange={(value) => handleChange("conference", value)}>
                      <SelectTrigger id="conference">
                        <SelectValue placeholder="Select conference" />
                      </SelectTrigger>
                      <SelectContent>
                        {userConferences.map((conference) => (
                          <SelectItem key={conference.id} value={conference.name}>
                            {conference.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      id="conference"
                      name="conference"
                      placeholder="Harvard National Model United Nations"
                      value={formData.conference}
                      onChange={handleInputChange}
                      required
                    />
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="committee">Committee *</Label>
                  <Input
                    id="committee"
                    name="committee"
                    placeholder="UN Security Council"
                    value={formData.committee}
                    onChange={handleInputChange}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="topic">Topic *</Label>
                  <Input
                    id="topic"
                    name="topic"
                    placeholder="Climate Change and Environmental Security"
                    value={formData.topic}
                    onChange={handleInputChange}
                    required
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
                    required
                  />
                </div>
              </CardContent>
              <CardFooter className="flex justify-end">
                <Button onClick={handleNext}>
                  Next
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>Background Information</CardTitle>
                <CardDescription>
                  Upload a background guide or paste text to help generate your position paper
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Tabs defaultValue="paste">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="upload">Upload Document</TabsTrigger>
                    <TabsTrigger value="paste">Paste Text</TabsTrigger>
                  </TabsList>
                  <TabsContent value="upload" className="space-y-4 pt-4">
                    <div className="flex items-center justify-center w-full">
                      <label
                        htmlFor="dropzone-file"
                        className="flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-lg cursor-pointer bg-muted/30 hover:bg-muted/50"
                      >
                        <div className="flex flex-col items-center justify-center pt-5 pb-6">
                          <Upload className="w-10 h-10 mb-3 text-muted-foreground" />
                          <p className="mb-2 text-sm text-muted-foreground">
                            <span className="font-semibold">Click to upload</span> or drag and drop
                          </p>
                          <p className="text-xs text-muted-foreground">TXT, PDF or DOCX (MAX. 10MB)</p>
                        </div>
                        <input 
                          id="dropzone-file" 
                          type="file" 
                          className="hidden" 
                          accept=".txt,.pdf,.docx" 
                          onChange={handleFileUpload}
                        />
                      </label>
                    </div>
                  </TabsContent>
                  <TabsContent value="paste" className="space-y-4 pt-4">
                    <div className="space-y-2">
                      <Label htmlFor="backgroundText">Background Information</Label>
                      <Textarea
                        id="backgroundText"
                        name="backgroundText"
                        placeholder="Paste background information or research notes here..."
                        className="min-h-[200px]"
                        value={formData.backgroundText}
                        onChange={handleInputChange}
                      />
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
              <CardFooter className="flex justify-between">
                <Button variant="outline" onClick={handleBack}>
                  <ChevronLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
                <Button onClick={handleNext}>
                  Next
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        )}

        {step === 3 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>Formatting Requirements</CardTitle>
                <CardDescription>Select a template or specify custom formatting requirements</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-4">
                  <Label>Select Template</Label>
                  <div className="grid gap-4 md:grid-cols-3">
                    {[
                      { id: 1, name: "Standard Position Paper", description: "Traditional format with introduction, body, and conclusion" },
                      { id: 2, name: "Harvard Style", description: "Specific format required for Harvard MUN conferences" },
                      { id: 3, name: "Detailed Analysis", description: "In-depth analysis with policy recommendations" },
                    ].map((template) => (
                      <div
                        key={template.id}
                        className={`cursor-pointer rounded-lg border p-4 transition-all hover:border-primary ${
                          formData.template === template.name ? "border-2 border-primary bg-primary/5" : ""
                        }`}
                        onClick={() => handleChange("template", template.name)}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="h-5 w-5 text-primary" />
                          <h3 className="font-medium">{template.name}</h3>
                        </div>
                        <p className="text-sm text-muted-foreground">{template.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <Separator className="my-4" />
                <div className="space-y-2">
                  <Label htmlFor="customRequirements">Custom Requirements (Optional)</Label>
                  <Textarea
                    id="customRequirements"
                    name="customRequirements"
                    placeholder="Enter any specific formatting requirements for your position paper..."
                    className="min-h-[100px]"
                    value={formData.customRequirements}
                    onChange={handleInputChange}
                  />
                </div>
              </CardContent>
              <CardFooter className="flex justify-between">
                <Button variant="outline" onClick={handleBack}>
                  <ChevronLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
                <Button onClick={handleNext}>
                  Next
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        )}

        {step === 4 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>Review and Generate</CardTitle>
                <CardDescription>Review your selections and generate your position paper</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg bg-muted p-4">
                  <h3 className="font-medium mb-2">Summary</h3>
                  <div className="grid gap-2 text-sm">
                    <div className="grid grid-cols-3">
                      <span className="text-muted-foreground">Conference:</span>
                      <span className="col-span-2 font-medium">{formData.conference || "Not selected"}</span>
                    </div>
                    <div className="grid grid-cols-3">
                      <span className="text-muted-foreground">Committee:</span>
                      <span className="col-span-2 font-medium">{formData.committee || "Not selected"}</span>
                    </div>
                    <div className="grid grid-cols-3">
                      <span className="text-muted-foreground">Topic:</span>
                      <span className="col-span-2 font-medium">{formData.topic || "Not selected"}</span>
                    </div>
                    <div className="grid grid-cols-3">
                      <span className="text-muted-foreground">Country/Character:</span>
                      <span className="col-span-2 font-medium">{formData.country || "Not selected"}</span>
                    </div>
                    <div className="grid grid-cols-3">
                      <span className="text-muted-foreground">Template:</span>
                      <span className="col-span-2 font-medium">{formData.template || "Not selected"}</span>
                    </div>
                    <div className="grid grid-cols-3">
                      <span className="text-muted-foreground">Background Info:</span>
                      <span className="col-span-2 font-medium">{formData.backgroundText ? "Provided" : "Not provided"}</span>
                    </div>
                  </div>
                </div>
                <div className="rounded-lg border p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="h-5 w-5 text-primary" />
                    <h3 className="font-medium">AI-Powered Generation</h3>
                  </div>
                  <p className="text-sm text-muted-foreground mb-4">
                    Our AI will analyze your inputs and generate a position paper tailored to your specifications.
                    You'll be able to edit and refine the document after generation.
                  </p>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-muted-foreground">Estimated time:</span>
                    <span className="font-medium">1-2 minutes</span>
                  </div>
                </div>
              </CardContent>
              <CardFooter className="flex justify-between">
                <Button variant="outline" onClick={handleBack}>
                  <ChevronLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
                <Button onClick={generatePositionPaper} disabled={isLoading}>
                  <Sparkles className="mr-2 h-4 w-4" />
                  {isLoading ? "Generating..." : "Generate Position Paper"}
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        )}

        {step === 5 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>Edit Position Paper</CardTitle>
                <CardDescription>Review and make changes to your generated position paper</CardDescription>
              </CardHeader>
              <CardContent>
                <RichTextEditor
                  initialValue={generatedContent}
                  height={600}
                  onChange={(content) => setGeneratedContent(content)}
                />
              </CardContent>
              <CardFooter className="flex justify-between">
                <Button variant="outline" onClick={() => setStep(4)}>
                  <ChevronLeft className="mr-2 h-4 w-4" />
                  Back
                </Button>
                <Button onClick={() => saveDocument(generatedContent)} disabled={isLoading}>
                  <Save className="mr-2 h-4 w-4" />
                  {isLoading ? "Saving..." : "Save Document"}
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        )}
      </div>
      <Toaster />
    </DashboardLayout>
  )
}

