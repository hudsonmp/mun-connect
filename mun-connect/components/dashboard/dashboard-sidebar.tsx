"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { PenTool, BookOpen, Users, Globe } from "lucide-react"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

// Define the feature categories and their sub-features
const featureCategories = [
  {
    id: "write",
    name: "Write",
    icon: PenTool,
    features: [
      "Rich text editor with AI insights",
      "Grammar analysis and corrections",
      "Guideline background paper formatting",
      "Realtime quick research assistance",
      "AI agent for personalized writing",
      "Writing suggestions based on profile",
      "Speech drafts",
      "Position papers",
      "Resolution papers",
      "Committee-specific documents",
      "Background guides",
      "Real-time editing with co-delegates",
    ],
  },
  {
    id: "prepare",
    name: "Prepare/Research",
    icon: BookOpen,
    features: [
      "Advanced research tools and AI assistance",
      "Perplexity/Gemini deep research integration",
      "Source finding and management",
      "Committee simulation for practice",
      "Speech practice and refinement",
      "Argument development with AI assistance",
      "Pre-conference preparation tools",
    ],
  },
  {
    id: "conference",
    name: "At Conference",
    icon: Users,
    features: [
      "Speech writer with real-time feedback",
      "Committee summarization tools",
      "Real-time paper writing assistance",
      "Network management with delegates",
      "In-platform committee chatting",
      "AI-powered listening and note-taking",
      "During-conference support tools",
    ],
  },
  {
    id: "network",
    name: "Network",
    icon: Globe,
    features: [
      "Publish and share papers",
      "Post-conference feedback tools",
      "Networking with diplomats",
      "Contact management for delegates",
      "Post-conference connection tools",
    ],
  },
]

export function DashboardSidebar() {
  const pathname = usePathname()
  const [hoveredCategory, setHoveredCategory] = useState<string | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div
      className={cn(
        "fixed left-0 top-16 h-[calc(100vh-4rem)] z-40 transition-all duration-300 ease-in-out",
        isExpanded ? "w-64" : "w-16",
      )}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => {
        setIsExpanded(false)
        setHoveredCategory(null)
      }}
    >
      <aside className="h-full bg-gradient-to-b from-blue-50 to-white dark:from-blue-950/30 dark:to-background border-r border-blue-200 dark:border-blue-800">
        <div
          className={cn(
            "p-4 font-medium text-sm text-blue-600 transition-opacity duration-300",
            isExpanded ? "opacity-100" : "opacity-0",
          )}
        >
          FEATURES
        </div>

        <nav className="flex-1">
          <ul className="space-y-1 px-2">
            {featureCategories.map((category) => (
              <li
                key={category.id}
                className="relative"
                onMouseEnter={() => isExpanded && setHoveredCategory(category.id)}
                onMouseLeave={() => setHoveredCategory(null)}
              >
                <Link
                  href={`/dashboard/${category.id}`}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all duration-300",
                    pathname.includes(`/dashboard/${category.id}`)
                      ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white"
                      : "hover:bg-blue-100/50 text-blue-800 dark:text-blue-200",
                    !isExpanded && "justify-center",
                  )}
                >
                  <category.icon className="h-5 w-5 flex-shrink-0" />
                  <span className={cn("transition-all duration-300", isExpanded ? "opacity-100" : "opacity-0 w-0")}>
                    {category.name}
                  </span>
                </Link>

                {/* Submenu that appears on hover */}
                {hoveredCategory === category.id && isExpanded && (
                  <div className="absolute left-full top-0 ml-2 w-64 rounded-md border border-blue-200 dark:border-blue-800 bg-gradient-to-br from-white to-blue-50 dark:from-gray-900 dark:to-blue-950/50 p-2 shadow-lg backdrop-blur-sm">
                    <ul className="space-y-1">
                      {category.features.map((feature, index) => (
                        <li key={index}>
                          <Link
                            href={`/dashboard/${category.id}/${index}`}
                            className="block rounded-md px-3 py-2 text-sm hover:bg-blue-100/50 dark:hover:bg-blue-900/20 text-blue-800 dark:text-blue-200"
                          >
                            {feature}
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </nav>

        <div
          className={cn(
            "absolute bottom-0 left-0 right-0 p-4 border-t border-blue-200 dark:border-blue-800 transition-all duration-300",
            isExpanded ? "opacity-100" : "opacity-0",
          )}
        >
          <div className="flex items-center gap-3">
            <Avatar className="h-8 w-8 border-2 border-blue-200 dark:border-blue-800">
              <AvatarImage src="/placeholder.svg?height=32&width=32" alt="User" />
              <AvatarFallback>UN</AvatarFallback>
            </Avatar>
            <div className={cn("transition-all duration-300", isExpanded ? "opacity-100" : "opacity-0")}>
              <p className="text-sm font-medium text-blue-800 dark:text-blue-200">Delegate Name</p>
              <p className="text-xs text-blue-600/70 dark:text-blue-400/70">United States</p>
            </div>
          </div>
        </div>
      </aside>
    </div>
  )
}

