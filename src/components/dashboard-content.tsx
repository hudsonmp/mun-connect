"use client"

import { useEffect, useState } from "react"
import { FileText, Plus, Calendar, Clock, Users, Flag, ChevronRight, Sparkles, FileEdit, Mic } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { motion } from "framer-motion"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from 'next/navigation'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useToast } from "@/components/ui/use-toast"

// Types for our data
interface Conference {
  id: number
  name: string
  acronym: string
  dates: string
  committee: string
  role: string
  status: string
  progress: number
}

interface Document {
  id: number
  title: string
  type: string
  committee: string
  conference: string
  updated_at: string
  progress: number
}

interface UserStats {
  id: number
  user_id: string
  conferences_count: number
  documents_count: number
  awards_count: number
}

export function DashboardContent() {
  const { user } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  const [conferences, setConferences] = useState<Conference[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [stats, setStats] = useState<UserStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Add dialog state
  const [isAddConferenceOpen, setIsAddConferenceOpen] = useState(false)
  const [conferenceForm, setConferenceForm] = useState({
    name: "",
    acronym: "",
    dates: "",
    committee: "",
    role: "",
    status: "upcoming"
  })
  const [isSaving, setIsSaving] = useState(false)

  // Format last edited time
  const formatLastEdited = (timestamp: string) => {
    if (!timestamp) return "";
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffInMs = now.getTime() - date.getTime();
    const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
    const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));
    
    if (diffInMinutes < 60) {
      return diffInMinutes === 1 ? "1 minute ago" : `${diffInMinutes} minutes ago`;
    } else if (diffInHours < 24) {
      return diffInHours === 1 ? "1 hour ago" : `${diffInHours} hours ago`;
    } else if (diffInDays < 7) {
      return diffInDays === 1 ? "1 day ago" : `${diffInDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!user) {
      router.push('/auth/login')
      return
    }

    async function fetchData() {
      setIsLoading(true)
      setError(null)

      try {
        // Fetch conferences from API
        const conferencesResponse = await fetch(`/api/conferences?userId=${user.id}`)
        if (!conferencesResponse.ok) {
          const errorData = await conferencesResponse.json()
          throw new Error(errorData.error || 'Failed to fetch conferences')
        }
        const conferenceData = await conferencesResponse.json()
        setConferences(conferenceData || [])

        // Fetch documents from API
        const documentsResponse = await fetch(`/api/documents?userId=${user.id}`)
        if (!documentsResponse.ok) {
          const errorData = await documentsResponse.json()
          throw new Error(errorData.error || 'Failed to fetch documents')
        }
        const documentData = await documentsResponse.json()
        setDocuments(documentData || [])

        // Fetch user stats
        const statsResponse = await fetch(`/api/user-stats?userId=${user.id}`)
        if (!statsResponse.ok) {
          const errorData = await statsResponse.json()
          throw new Error(errorData.error || 'Failed to fetch user stats')
        }
        const statsData = await statsResponse.json()
        setStats(statsData || null)

      } catch (err: any) {
        console.error('Error fetching data:', err)
        setError(err?.message || 'An unexpected error occurred while fetching data')
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [user, router])

  // Handle conference form changes
  const handleConferenceFormChange = (field: string, value: string) => {
    setConferenceForm({
      ...conferenceForm,
      [field]: value
    })
  }

  // Handle form input changes directly from input events
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setConferenceForm({
      ...conferenceForm,
      [name]: value
    })
  }

  // Submit conference form
  const handleSubmitConference = async () => {
    if (!user || !user.id) {
      console.error("User not authenticated or missing ID:", user);
      toast({
        title: "Authentication required",
        description: "Please sign in to add a conference",
        variant: "destructive"
      });
      return;
    }

    // Validate form
    if (!conferenceForm.name || !conferenceForm.committee || !conferenceForm.role) {
      toast({
        title: "Missing information",
        description: "Please fill out all required fields",
        variant: "destructive"
      })
      return
    }

    setIsSaving(true)
    console.log("Submitting conference with user ID:", user.id);

    try {
      // Create acronym if not provided
      const acronym = conferenceForm.acronym || conferenceForm.name
        .split(' ')
        .map(word => word[0])
        .join('')
        .toUpperCase()

      const response = await fetch('/api/conferences', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'user-id': user.id,
        },
        body: JSON.stringify({
          user_id: user.id,
          name: conferenceForm.name,
          acronym: acronym,
          dates: conferenceForm.dates,
          committee: conferenceForm.committee,
          role: conferenceForm.role,
          status: conferenceForm.status,
          progress: 0
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to create conference')
      }

      const newConference = await response.json()
      
      // Update conferences list with new conference
      setConferences([...conferences, newConference])
      
      // Reset form
      setConferenceForm({
        name: "",
        acronym: "",
        dates: "",
        committee: "",
        role: "",
        status: "upcoming"
      })
      
      // Close dialog
      setIsAddConferenceOpen(false)
      
      toast({
        title: "Conference added",
        description: "Your conference has been successfully added"
      })
      
      // Update stats if we have them
      if (stats) {
        setStats({
          ...stats,
          conferences_count: stats.conferences_count + 1
        })
      }
    } catch (err: any) {
      console.error('Error creating conference:', err)
      toast({
        title: "Error adding conference",
        description: err?.message || "An unexpected error occurred",
        variant: "destructive"
      })
    } finally {
      setIsSaving(false)
    }
  }

  // If not authenticated, don't render anything (will redirect)
  if (!user) {
    return null
  }

  // Fallback stats if not loaded yet
  const displayStats = [
    {
      title: "Total Conferences",
      value: stats ? stats.conferences_count.toString() : "0",
      icon: Calendar,
      description: "Your MUN conferences",
    },
    {
      title: "Documents Created",
      value: stats ? stats.documents_count.toString() : "0",
      icon: FileText,
      description: "Position papers, resolutions, speeches",
    },
    {
      title: "Awards Won",
      value: stats ? stats.awards_count.toString() : "0",
      icon: Sparkles,
      description: "Best Delegate, Outstanding Delegate",
    },
  ]

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold tracking-tight">Loading...</h1>
          <p className="text-muted-foreground">Fetching your MUN activities</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-3xl font-bold tracking-tight">Error</h1>
          <p className="text-muted-foreground">{error}</p>
          <Button className="mt-4 w-fit" onClick={() => window.location.reload()}>
            Try Again
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Welcome back, {user?.email?.split('@')[0] || "User"}</h1>
        <p className="text-muted-foreground">Here's what's happening with your MUN activities</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {displayStats.map((stat, index) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                <stat.icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">{stat.description}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <Tabs defaultValue="conferences" className="space-y-4">
        <TabsList>
          <TabsTrigger value="conferences">Conferences</TabsTrigger>
          <TabsTrigger value="documents">Recent Documents</TabsTrigger>
        </TabsList>
        <TabsContent value="conferences" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {conferences.map((conference, index) => (
              <motion.div
                key={conference.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <ConferenceCard conference={conference} />
              </motion.div>
            ))}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: conferences.length * 0.1 }}
            >
              <Card className="flex h-full flex-col items-center justify-center p-6 border-dashed">
                <div className="flex flex-col items-center gap-2 text-center">
                  <div className="rounded-full bg-primary/10 p-3">
                    <Plus className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="text-lg font-medium">Add Conference</h3>
                  <p className="text-sm text-muted-foreground">Register a new conference you're participating in</p>
                  <Button className="mt-2" onClick={() => setIsAddConferenceOpen(true)}>Add Conference</Button>
                </div>
              </Card>
            </motion.div>
          </div>
        </TabsContent>
        <TabsContent value="documents" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {documents.map((document, index) => (
              <motion.div
                key={document.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <DocumentCard document={{
                  ...document,
                  lastEdited: formatLastEdited(document.updated_at)
                }} />
              </motion.div>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      <div className="mt-4">
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
            <ActionCard
              title="New Position Paper"
              description="Create a position paper for your committee"
              icon={FileEdit}
              href="/documents/new/position-paper"
            />
          </motion.div>
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}>
            <ActionCard
              title="New Resolution"
              description="Draft a resolution for your committee"
              icon={FileText}
              href="/documents/new/resolution"
            />
          </motion.div>
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}>
            <ActionCard
              title="New Speech"
              description="Prepare a speech for your committee"
              icon={Mic}
              href="/speeches/new"
            />
          </motion.div>
        </div>
      </div>

      {/* Add Conference Dialog */}
      <Dialog open={isAddConferenceOpen} onOpenChange={setIsAddConferenceOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Add New Conference</DialogTitle>
            <DialogDescription>
              Enter the details of the conference you're participating in.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="name" className="text-right">
                Name *
              </Label>
              <Input
                id="name"
                name="name"
                value={conferenceForm.name}
                onChange={handleInputChange}
                className="col-span-3"
                placeholder="Harvard National Model United Nations"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="acronym" className="text-right">
                Acronym
              </Label>
              <Input
                id="acronym"
                name="acronym"
                value={conferenceForm.acronym}
                onChange={handleInputChange}
                className="col-span-3"
                placeholder="HNMUN"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="dates" className="text-right">
                Dates
              </Label>
              <Input
                id="dates"
                name="dates"
                value={conferenceForm.dates}
                onChange={handleInputChange}
                className="col-span-3"
                placeholder="Feb 10-13, 2024"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="committee" className="text-right">
                Committee *
              </Label>
              <Input
                id="committee"
                name="committee"
                value={conferenceForm.committee}
                onChange={handleInputChange}
                className="col-span-3"
                placeholder="UN Security Council"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="role" className="text-right">
                Role *
              </Label>
              <Input
                id="role"
                name="role"
                value={conferenceForm.role}
                onChange={handleInputChange}
                className="col-span-3"
                placeholder="Delegate of France"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="status" className="text-right">
                Status
              </Label>
              <Select
                value={conferenceForm.status}
                onValueChange={(value) => handleConferenceFormChange("status", value)}
              >
                <SelectTrigger className="col-span-3">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="upcoming">Upcoming</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddConferenceOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmitConference} disabled={isSaving}>
              {isSaving ? "Adding..." : "Add Conference"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function ConferenceCard({ conference }: { conference: any }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle>{conference.acronym}</CardTitle>
          <StatusBadge status={conference.status} />
        </div>
        <CardDescription className="line-clamp-1">{conference.name}</CardDescription>
      </CardHeader>
      <CardContent className="pb-2">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{conference.dates}</span>
          </div>
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{conference.committee}</span>
          </div>
          <div className="flex items-center gap-2">
            <Flag className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{conference.role}</span>
          </div>
          <div className="pt-2">
            <div className="flex items-center justify-between text-sm mb-1">
              <span>Preparation</span>
              <span>{conference.progress}%</span>
            </div>
            <Progress value={conference.progress} className="h-2" />
          </div>
        </div>
      </CardContent>
      <CardFooter>
        <Button variant="ghost" size="sm" className="w-full justify-between">
          View Details
          <ChevronRight className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  )
}

function DocumentCard({ document }: { document: any }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle className="text-base">{document.title}</CardTitle>
          <TypeBadge type={document.type} />
        </div>
        <CardDescription className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          <span>Edited {document.lastEdited}</span>
        </CardDescription>
      </CardHeader>
      <CardContent className="pb-2">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{document.committee}</span>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm">{document.conference}</span>
          </div>
          <div className="pt-2">
            <div className="flex items-center justify-between text-sm mb-1">
              <span>Progress</span>
              <span>{document.progress}%</span>
            </div>
            <Progress value={document.progress} className="h-2" />
          </div>
        </div>
      </CardContent>
      <CardFooter>
        <Button variant="ghost" size="sm" className="w-full justify-between">
          Edit Document
          <ChevronRight className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  )
}

function ActionCard({
  title,
  description,
  icon: Icon,
  href,
}: {
  title: string
  description: string
  icon: any
  href: string
}) {
  return (
    <Card className="overflow-hidden transition-all hover:shadow-md">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <div className="rounded-md bg-primary/10 p-2">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <CardTitle className="text-lg">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pb-2">
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
      <CardFooter>
        <Button asChild className="w-full">
          <a href={href}>Create Now</a>
        </Button>
      </CardFooter>
    </Card>
  )
}

function StatusBadge({ status }: { status: string }) {
  let variant: "default" | "secondary" | "outline" = "default"

  if (status === "upcoming") {
    variant = "secondary"
  } else if (status === "completed") {
    variant = "outline"
  }

  return (
    <Badge variant={variant} className="capitalize">
      {status}
    </Badge>
  )
}

function TypeBadge({ type }: { type: string }) {
  let variant: "default" | "secondary" | "outline" = "default"

  if (type === "Resolution") {
    variant = "secondary"
  } else if (type === "Speech") {
    variant = "outline"
  }

  return (
    <Badge variant={variant} className="capitalize">
      {type}
    </Badge>
  )
}

