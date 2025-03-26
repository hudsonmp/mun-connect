"use client"
import { FileText, Plus, Calendar, Clock, Users, Flag, ChevronRight, Sparkles, FileEdit, Mic } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { motion } from "framer-motion"

// Mock data
const conferences = [
  {
    id: 1,
    name: "Harvard National Model United Nations",
    acronym: "HNMUN",
    dates: "Feb 15-18, 2024",
    committee: "UN Security Council",
    role: "France",
    status: "active",
    progress: 75,
  },
  {
    id: 2,
    name: "Yale Model United Nations",
    acronym: "YMUN",
    dates: "Jan 19-22, 2024",
    committee: "World Health Organization",
    role: "Germany",
    status: "upcoming",
    progress: 30,
  },
  {
    id: 3,
    name: "Princeton Model United Nations Conference",
    acronym: "PMUNC",
    dates: "Nov 16-19, 2023",
    committee: "UN General Assembly",
    role: "Japan",
    status: "completed",
    progress: 100,
  },
]

const documents = [
  {
    id: 1,
    title: "Climate Change Position Paper",
    type: "Position Paper",
    committee: "UN Security Council",
    conference: "HNMUN",
    lastEdited: "2 days ago",
    progress: 80,
  },
  {
    id: 2,
    title: "Resolution on Global Health Crisis",
    type: "Resolution",
    committee: "World Health Organization",
    conference: "YMUN",
    lastEdited: "1 week ago",
    progress: 45,
  },
  {
    id: 3,
    title: "Opening Speech on Nuclear Disarmament",
    type: "Speech",
    committee: "UN General Assembly",
    conference: "PMUNC",
    lastEdited: "3 weeks ago",
    progress: 100,
  },
]

const stats = [
  {
    title: "Total Conferences",
    value: "8",
    icon: Calendar,
    description: "Across 3 years",
  },
  {
    title: "Documents Created",
    value: "24",
    icon: FileText,
    description: "Position papers, resolutions, speeches",
  },
  {
    title: "Awards Won",
    value: "3",
    icon: Sparkles,
    description: "Best Delegate, Outstanding Delegate",
  },
]

export function DashboardContent() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Welcome back, Sarah</h1>
        <p className="text-muted-foreground">Here's what's happening with your MUN activities</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {stats.map((stat, index) => (
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
                  <Button className="mt-2">Add Conference</Button>
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
                <DocumentCard document={document} />
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

