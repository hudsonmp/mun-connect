"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { PenTool, BookOpen, Users, Globe, MessageSquare, FileText, Sparkles, Zap, ArrowRight, ExternalLink } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "./ui/card"
import { Button } from "./ui/button"
import Link from "next/link"

const features = [
  {
    icon: PenTool,
    title: "AI-Powered Writing",
    description: "Create compelling position papers, speeches, and resolutions with our AI writing assistant.",
    backDescription:
      "Our advanced AI analyzes successful MUN documents to help you craft persuasive arguments and polished papers.",
    link: "/features/ai-writing",
    dashboardLink: "/dashboard/write",
  },
  {
    icon: BookOpen,
    title: "Research Tools",
    description: "Access comprehensive research tools and resources to prepare for your committees.",
    backDescription:
      "Leverage AI-powered research assistants that find, summarize, and organize relevant information for your position.",
    link: "/features/research-tools",
    dashboardLink: "/dashboard/prepare",
  },
  {
    icon: Users,
    title: "Committee Simulation",
    description: "Practice with AI-simulated committee sessions to perfect your diplomacy skills.",
    backDescription:
      "Engage with AI delegates that respond realistically to your arguments and help you prepare for actual committee dynamics.",
    link: "/features/committee-simulation",
    dashboardLink: "/dashboard/conference",
  },
  {
    icon: Globe,
    title: "Global Networking",
    description: "Connect with MUN delegates and diplomats from around the world.",
    backDescription:
      "Build your professional network with like-minded delegates and real diplomats through our verified connection platform.",
    link: "/features/global-networking",
    dashboardLink: "/dashboard/network",
  },
  {
    icon: MessageSquare,
    title: "Real-time Collaboration",
    description: "Collaborate with your delegation in real-time during conferences.",
    backDescription:
      "Share notes, draft resolutions together, and coordinate strategy with your team members during live committee sessions.",
    link: "/features/real-time-collaboration",
    dashboardLink: "/dashboard/conference",
  },
  {
    icon: FileText,
    title: "Document Management",
    description: "Organize all your MUN documents in one secure, accessible place.",
    backDescription:
      "Store, categorize, and quickly retrieve your position papers, speeches, and resolutions with our cloud-based system.",
    link: "/features/document-management",
    dashboardLink: "/dashboard/write",
  },
  {
    icon: Sparkles,
    title: "AI Feedback",
    description: "Receive instant feedback on your speeches and papers from our AI assistant.",
    backDescription:
      "Get detailed suggestions on content, structure, and diplomatic language to improve your MUN performance.",
    link: "/features/ai-feedback",
    dashboardLink: "/dashboard/write",
  },
  {
    icon: Zap,
    title: "Conference Tracking",
    description: "Track your participation and achievements across multiple conferences.",
    backDescription:
      "Build a portfolio of your MUN experience with detailed analytics on your performance and growth over time.",
    link: "/features/conference-tracking",
    dashboardLink: "/dashboard/conference",
  },
]

export function LandingFeatures() {
  return (
    <section className="py-20 bg-gradient-to-b from-background to-muted/50">
      <div className="container px-4 mx-auto">
        <div className="mx-auto max-w-3xl text-center mb-16">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl">Features That Set Us Apart</h2>
          <p className="mt-4 text-muted-foreground">
            Designed by MUN delegates, for MUN delegates. Our platform offers everything you need to excel.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature, index) => (
            <FeatureCard key={index} feature={feature} index={index} />
          ))}
        </div>
      </div>
    </section>
  )
}

function FeatureCard({ feature, index }: { feature: (typeof features)[0]; index: number }) {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      viewport={{ once: true }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="h-full"
    >
      <Card 
        className={`h-full overflow-hidden transition-all duration-300 ${
          isHovered 
            ? "bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-lg" 
            : "bg-gradient-to-br from-blue-50 to-indigo-50 hover:from-blue-100 hover:to-indigo-100"
        }`}
      >
        <CardHeader className="pb-2">
          <div className="flex justify-between items-start">
            <feature.icon className={`h-10 w-10 ${isHovered ? "text-white" : "text-primary"}`} />
          </div>
          <CardTitle className={`mt-4 ${isHovered ? "text-white" : ""}`}>{feature.title}</CardTitle>
        </CardHeader>
        
        <CardContent>
          <div className="transition-all duration-300">
            {isHovered ? (
              <p className="text-blue-50">{feature.description}</p>
            ) : (
              <CardDescription>{feature.title}</CardDescription>
            )}
          </div>
        </CardContent>
        
        {isHovered && (
          <CardFooter className="flex gap-2 pt-2">
            <Link href={feature.dashboardLink} className="flex-1">
              <Button 
                variant="secondary" 
                className="w-full bg-white text-blue-600 hover:bg-blue-50"
              >
                Try it <ExternalLink className="ml-1 h-4 w-4" />
              </Button>
            </Link>
            <Link href={feature.link} className="flex-1">
              <Button 
                variant="outline" 
                className="w-full border-white text-white hover:bg-blue-700"
              >
                Learn more <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            </Link>
          </CardFooter>
        )}
      </Card>
    </motion.div>
  )
}

