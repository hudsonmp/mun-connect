"use client"

import { useState } from "react"
import { DashboardLayout } from "@/components/dashboard-layout"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { ChevronLeft, ChevronRight, Upload, FileText, Sparkles } from "lucide-react"
import { motion } from "framer-motion"

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
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    conference: "",
    committee: "",
    topic: "",
    country: "",
    backgroundGuide: null,
    template: "",
  })

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
                <CardDescription>Select the conference, committee, topic, and your country/character</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="conference">Conference</Label>
                  <Select value={formData.conference} onValueChange={(value) => handleChange("conference", value)}>
                    <SelectTrigger id="conference">
                      <SelectValue placeholder="Select conference" />
                    </SelectTrigger>
                    <SelectContent>
                      {conferences.map((conference) => (
                        <SelectItem key={conference.id} value={conference.name}>
                          {conference.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="committee">Committee</Label>
                  <Select value={formData.committee} onValueChange={(value) => handleChange("committee", value)}>
                    <SelectTrigger id="committee">
                      <SelectValue placeholder="Select committee" />
                    </SelectTrigger>
                    <SelectContent>
                      {committees.map((committee) => (
                        <SelectItem key={committee.id} value={committee.name}>
                          {committee.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="topic">Topic</Label>
                  <Select value={formData.topic} onValueChange={(value) => handleChange("topic", value)}>
                    <SelectTrigger id="topic">
                      <SelectValue placeholder="Select topic" />
                    </SelectTrigger>
                    <SelectContent>
                      {topics.map((topic) => (
                        <SelectItem key={topic.id} value={topic.name}>
                          {topic.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="country">Country/Character</Label>
                  <Select value={formData.country} onValueChange={(value) => handleChange("country", value)}>
                    <SelectTrigger id="country">
                      <SelectValue placeholder="Select country/character" />
                    </SelectTrigger>
                    <SelectContent>
                      {countries.map((country) => (
                        <SelectItem key={country.id} value={country.name}>
                          {country.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
                <Tabs defaultValue="upload">
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
                          <p className="text-xs text-muted-foreground">PDF or DOCX (MAX. 10MB)</p>
                        </div>
                        <input id="dropzone-file" type="file" className="hidden" />
                      </label>
                    </div>
                  </TabsContent>
                  <TabsContent value="paste" className="space-y-4 pt-4">
                    <div className="space-y-2">
                      <Label htmlFor="background-text">Background Information</Label>
                      <Textarea
                        id="background-text"
                        placeholder="Paste background information or research notes here..."
                        className="min-h-[200px]"
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
                    {templates.map((template) => (
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
                  <Label htmlFor="custom-requirements">Custom Requirements (Optional)</Label>
                  <Textarea
                    id="custom-requirements"
                    placeholder="Enter any specific formatting requirements for your position paper..."
                    className="min-h-[100px]"
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
                <Button>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Generate Position Paper
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        )}
      </div>
    </DashboardLayout>
  )
}

