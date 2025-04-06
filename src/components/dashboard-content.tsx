"use client"

import { useEffect, useState } from "react"
import { FileText, Plus, Clock, Flag } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from 'next/navigation'
import { useToast } from "@/components/ui/use-toast"
import { createClient } from '@supabase/supabase-js'

// Get environment variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

// Simple types for our data
interface Conference {
  id: number
  name: string
  committee: string
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
  conferences_count: number
  documents_count: number
  awards_count: number
}

export function DashboardContent() {
  const { user } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  const [data, setData] = useState<{
    conferences: Conference[]
    documents: Document[]
    stats: UserStats
    isLoading: boolean
    error: string | null
  }>({
    conferences: [],
    documents: [],
    stats: { conferences_count: 0, documents_count: 0, awards_count: 0 },
    isLoading: true,
    error: null
  })

  // Format time
  const formatLastEdited = (timestamp: string) => {
    if (!timestamp) return ""
    
    const date = new Date(timestamp)
    const now = new Date()
    const diffInMs = now.getTime() - date.getTime()
    const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60))
    
    if (diffInHours < 24) {
      return diffInHours <= 1 ? "1 hour ago" : `${diffInHours} hours ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  // Fetch data
  useEffect(() => {
    if (!user) {
      router.push('/auth/login')
      return
    }

    const fetchData = async () => {
      try {
        // Create Supabase client
        const supabase = createClient(supabaseUrl, supabaseKey)
        
        // Fetch conferences
        const { data: conferencesData, error: conferencesError } = await supabase
          .from('conferences')
          .select('*')
          .eq('user_id', user.id)
          .order('created_at', { ascending: false })
          .limit(3)
        
        // Fetch documents
        const { data: documentsData, error: documentsError } = await supabase
          .from('documents')
          .select('*')
          .eq('user_id', user.id)
          .order('updated_at', { ascending: false })
          .limit(3)
        
        // Fetch stats
        const { data: statsData } = await supabase
          .from('user_stats')
          .select('*')
          .eq('user_id', user.id)
          .single()
        
        // Update state with data
        setData({
          conferences: conferencesData || [],
          documents: documentsData || [],
          stats: statsData || { conferences_count: 0, documents_count: 0, awards_count: 0 },
          isLoading: false,
          error: conferencesError || documentsError ? 'Error fetching data' : null
        })
      } catch (err) {
        console.error('Error fetching dashboard data:', err)
        setData(prev => ({ ...prev, isLoading: false, error: 'Failed to load dashboard data' }))
        
        toast({
          title: "Error",
          description: "Failed to load dashboard data. Please try again later.",
          variant: "destructive"
        })
      }
    }

    fetchData()
  }, [user, router, toast])

  // Display loading state
  if (data.isLoading) {
    return (
      <div className="flex justify-center items-center h-full">
        <p className="text-muted-foreground">Loading dashboard...</p>
      </div>
    )
  }

  // Display error state
  if (data.error) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="text-center">
          <p className="text-destructive mb-2">Failed to load dashboard data</p>
          <Button onClick={() => window.location.reload()}>Try Again</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Stats overview */}
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard title="Conferences" value={data.stats.conferences_count} icon={<Flag className="h-4 w-4" />} />
        <StatCard title="Documents" value={data.stats.documents_count} icon={<FileText className="h-4 w-4" />} />
        <StatCard title="Awards" value={data.stats.awards_count} icon={<Flag className="h-4 w-4" />} />
      </div>

      {/* Recent documents */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Recent Documents</h2>
          <Button size="sm" onClick={() => router.push('/documents')}>View All</Button>
        </div>
        
        <div className="grid gap-4">
          {data.documents.length > 0 ? (
            data.documents.map(document => (
              <DocumentCard key={document.id} document={document} formatTime={formatLastEdited} />
            ))
          ) : (
            <Card>
              <CardContent className="p-6 text-center">
                <p className="text-muted-foreground mb-4">No documents yet</p>
                <Button onClick={() => router.push('/documents/new')}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Document
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Upcoming conferences */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Upcoming Conferences</h2>
          <Button size="sm" onClick={() => router.push('/conferences')}>View All</Button>
        </div>
        
        <div className="grid gap-4">
          {data.conferences.length > 0 ? (
            data.conferences.map(conference => (
              <ConferenceCard key={conference.id} conference={conference} />
            ))
          ) : (
            <Card>
              <CardContent className="p-6 text-center">
                <p className="text-muted-foreground mb-4">No conferences yet</p>
                <Button onClick={() => router.push('/conferences/new')}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Conference
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

// Simple reusable components
function StatCard({ title, value, icon }: { title: string; value: number; icon: React.ReactNode }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-semibold">{value}</p>
          </div>
          <div className="rounded-full bg-primary/10 p-2 text-primary">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function ConferenceCard({ conference }: { conference: Conference }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <CardTitle className="text-lg">{conference.name}</CardTitle>
          <StatusBadge status={conference.status} />
        </div>
        <CardDescription>{conference.committee}</CardDescription>
      </CardHeader>
      <CardContent className="pb-2">
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span>{conference.progress}%</span>
          </div>
          <Progress value={conference.progress} className="h-2" />
        </div>
      </CardContent>
      <CardFooter>
        <Button variant="outline" size="sm" className="w-full">
          View Details
        </Button>
      </CardFooter>
    </Card>
  )
}

function DocumentCard({ document, formatTime }: { document: Document; formatTime: (time: string) => string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <CardTitle className="text-lg">{document.title}</CardTitle>
          <TypeBadge type={document.type} />
        </div>
        <CardDescription>{document.committee} • {document.conference}</CardDescription>
      </CardHeader>
      <CardContent className="pb-2">
        <div className="flex items-center text-sm text-muted-foreground">
          <Clock className="h-3.5 w-3.5 mr-1" />
          <span>Updated {formatTime(document.updated_at)}</span>
        </div>
      </CardContent>
      <CardFooter>
        <Button variant="outline" size="sm" className="w-full">
          View Document
        </Button>
      </CardFooter>
    </Card>
  )
}

function StatusBadge({ status }: { status: string }) {
  const variant = status === 'completed' 
    ? 'default' 
    : status === 'upcoming' 
    ? 'secondary' 
    : 'outline'
  
  return <Badge variant={variant as any}>{status}</Badge>
}

function TypeBadge({ type }: { type: string }) {
  return <Badge variant="outline">{type}</Badge>
}

