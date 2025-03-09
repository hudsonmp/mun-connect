import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Users, MessageSquare, FileText, NotebookPen, MessageCircle } from "lucide-react"

// Sub-features for the Conference section
const conferenceFeatures = [
  {
    id: "speech-writer",
    name: "Speech Writer",
    description: "Create speeches with real-time feedback during conferences",
    icon: MessageSquare,
    href: "/dashboard/conference/speech-writer",
  },
  {
    id: "committee-summary",
    name: "Committee Summarization",
    description: "AI-powered tools to summarize committee discussions",
    icon: NotebookPen,
    href: "/dashboard/conference/committee-summary",
  },
  {
    id: "paper-writing",
    name: "Paper Writing",
    description: "Real-time assistance for writing papers during conferences",
    icon: FileText,
    href: "/dashboard/conference/paper-writing",
  },
  {
    id: "delegate-network",
    name: "Delegate Network",
    description: "Manage your connections with other delegates",
    icon: Users,
    href: "/dashboard/conference/delegate-network",
  },
  {
    id: "committee-chat",
    name: "Committee Chat",
    description: "In-platform chatting with committee members",
    icon: MessageCircle,
    href: "/dashboard/conference/committee-chat",
  },
]

export default function ConferenceDashboardPage() {
  return (
    <div className="space-y-6 w-full max-w-full">
      <div>
        <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          At Conference
        </h1>
        <p className="text-base text-muted-foreground mt-2">
          Tools and resources to help you succeed during your Model UN conferences.
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {conferenceFeatures.map((feature) => (
          <Card 
            key={feature.id}
            className="overflow-hidden border-blue-200 dark:border-blue-800 hover:shadow-md transition-all group"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-indigo-500/10 pointer-events-none" />
            <CardHeader className="pb-2 relative">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 group-hover:bg-blue-200 dark:group-hover:bg-blue-800/50 transition-colors">
                  <feature.icon className="h-5 w-5" />
                </div>
                <CardTitle className="text-xl">{feature.name}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="relative">
              <CardDescription className="mb-4">{feature.description}</CardDescription>
              <Button 
                variant="outline" 
                className="w-full hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20"
                asChild
              >
                <a href={feature.href}>Open</a>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
} 