import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { PenTool, FileText, MessageSquare, Users, Sparkles } from "lucide-react"

// Sub-features for the Write section
const writeFeatures = [
  {
    id: "editor",
    name: "Rich Text Editor",
    description: "Create and edit documents with AI-powered insights",
    icon: PenTool,
    href: "/dashboard/write/editor",
  },
  {
    id: "position-papers",
    name: "Position Papers",
    description: "Draft and manage your position papers",
    icon: FileText,
    href: "/dashboard/write/position-papers",
  },
  {
    id: "speech-drafts",
    name: "Speech Drafts",
    description: "Create compelling speeches for your committee",
    icon: MessageSquare,
    href: "/dashboard/write/speech-drafts",
  },
  {
    id: "resolutions",
    name: "Resolution Papers",
    description: "Draft and collaborate on resolution papers",
    icon: Users,
    href: "/dashboard/write/resolutions",
  },
  {
    id: "ai-assistant",
    name: "AI Writing Assistant",
    description: "Get personalized writing suggestions based on your profile",
    icon: Sparkles,
    href: "/dashboard/write/ai-assistant",
  },
]

export default function WriteDashboardPage() {
  return (
    <div className="space-y-6 w-full max-w-full">
      <div>
        <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          Write
        </h1>
        <p className="text-base text-muted-foreground mt-2">
          Create, edit, and manage your Model UN documents with AI assistance.
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {writeFeatures.map((feature) => (
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