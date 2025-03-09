import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { BookOpen, Search, FileText, Presentation, Brain } from "lucide-react"

// Sub-features for the Prepare/Research section
const prepareFeatures = [
  {
    id: "research-tools",
    name: "Research Tools",
    description: "Advanced research tools with AI assistance",
    icon: Search,
    href: "/dashboard/prepare/research-tools",
  },
  {
    id: "source-management",
    name: "Source Management",
    description: "Find and manage sources for your research",
    icon: FileText,
    href: "/dashboard/prepare/source-management",
  },
  {
    id: "committee-simulation",
    name: "Committee Simulation",
    description: "Practice with AI-simulated committee scenarios",
    icon: Presentation,
    href: "/dashboard/prepare/committee-simulation",
  },
  {
    id: "speech-practice",
    name: "Speech Practice",
    description: "Practice and refine your speeches with AI feedback",
    icon: BookOpen,
    href: "/dashboard/prepare/speech-practice",
  },
  {
    id: "argument-development",
    name: "Argument Development",
    description: "Develop compelling arguments with AI assistance",
    icon: Brain,
    href: "/dashboard/prepare/argument-development",
  },
]

export default function PrepareDashboardPage() {
  return (
    <div className="space-y-6 w-full max-w-full">
      <div>
        <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          Prepare & Research
        </h1>
        <p className="text-base text-muted-foreground mt-2">
          Prepare for your conferences with advanced research tools and practice simulations.
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {prepareFeatures.map((feature) => (
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