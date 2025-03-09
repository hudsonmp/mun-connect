"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { PenTool, BookOpen, Users, Globe, MessageSquare, FileText, Sparkles, Zap } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import Link from "next/link"

const features = [
  {
    icon: PenTool,
    title: "AI-Powered Writing",
    description: "Create compelling position papers, speeches, and resolutions with our AI writing assistant.",
    backDescription:
      "Our advanced AI analyzes successful MUN documents to help you craft persuasive arguments and polished papers.",
    link: "/features/ai-writing",
  },
  {
    icon: BookOpen,
    title: "Research Tools",
    description: "Access comprehensive research tools and resources to prepare for your committees.",
    backDescription:
      "Leverage AI-powered research assistants that find, summarize, and organize relevant information for your position.",
    link: "/features/research-tools",
  },
  {
    icon: Users,
    title: "Committee Simulation",
    description: "Practice with AI-simulated committee sessions to perfect your diplomacy skills.",
    backDescription:
      "Engage with AI delegates that respond realistically to your arguments and help you prepare for actual committee dynamics.",
    link: "/features/committee-simulation",
  },
  {
    icon: Globe,
    title: "Global Networking",
    description: "Connect with MUN delegates and diplomats from around the world.",
    backDescription:
      "Build your professional network with like-minded delegates and real diplomats through our verified connection platform.",
    link: "/features/global-networking",
  },
  {
    icon: MessageSquare,
    title: "Real-time Collaboration",
    description: "Collaborate with your delegation in real-time during conferences.",
    backDescription:
      "Share notes, draft resolutions together, and coordinate strategy with your team members during live committee sessions.",
    link: "/features/real-time-collaboration",
  },
  {
    icon: FileText,
    title: "Document Management",
    description: "Organize all your MUN documents in one secure, accessible place.",
    backDescription:
      "Store, categorize, and quickly retrieve your position papers, speeches, and resolutions with our cloud-based system.",
    link: "/features/document-management",
  },
  {
    icon: Sparkles,
    title: "AI Feedback",
    description: "Receive instant feedback on your speeches and papers from our AI assistant.",
    backDescription:
      "Get detailed suggestions on content, structure, and diplomatic language to improve your MUN performance.",
    link: "/features/ai-feedback",
  },
  {
    icon: Zap,
    title: "Conference Tracking",
    description: "Track your participation and achievements across multiple conferences.",
    backDescription:
      "Build a portfolio of your MUN experience with detailed analytics on your performance and growth over time.",
    link: "/features/conference-tracking",
  },
]

export function LandingFeatures() {
  return (
    <section className="py-20 bg-gradient-to-b from-background to-muted/50">
      <div className="container">
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
  const [isFlipped, setIsFlipped] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      viewport={{ once: true }}
      className="perspective-1000"
      onMouseEnter={() => setIsFlipped(true)}
      onMouseLeave={() => setIsFlipped(false)}
    >
      <div
        className="relative w-full h-full transition-all duration-500 preserve-3d cursor-pointer"
        style={{
          transform: isFlipped ? "rotateY(180deg)" : "rotateY(0deg)",
          transformStyle: "preserve-3d",
        }}
      >
        {/* Front of card */}
        <Card className="h-full backface-hidden">
          <CardHeader>
            <feature.icon className="h-10 w-10 text-primary" />
            <CardTitle className="mt-4">{feature.title}</CardTitle>
          </CardHeader>
          <CardContent>
            <CardDescription>{feature.description}</CardDescription>
          </CardContent>
        </Card>

        {/* Back of card */}
        <Link href={feature.link} className="block h-full">
          <Card
            className="absolute inset-0 h-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white backface-hidden"
            style={{
              transform: "rotateY(180deg)",
              transformStyle: "preserve-3d",
            }}
          >
            <CardHeader>
              <feature.icon className="h-10 w-10 text-white" />
              <CardTitle className="mt-4 text-white">{feature.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-blue-100">{feature.backDescription}</p>
              <div className="mt-4 text-sm font-medium text-white flex items-center justify-end">
                Learn more
                <svg className="ml-1 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>
    </motion.div>
  )
}

