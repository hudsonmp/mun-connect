"use client"

import React from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "../../lib/auth-context"
import { Button } from "../../components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../components/ui/card"
import { Pencil, GraduationCap, Users, MapPin } from "lucide-react"

export default function DashboardPage() {
  const { user } = useAuth()
  const router = useRouter()

  const features = [
    {
      title: "Write",
      description: "Create and improve speeches with AI assistance",
      icon: <Pencil className="h-6 w-6 text-blue-600" />,
      href: "/dashboard/write",
    },
    {
      title: "Research",
      description: "Access powerful AI research tools for your position papers",
      icon: <GraduationCap className="h-6 w-6 text-indigo-600" />,
      href: "/dashboard/research",
    },
    {
      title: "At Conference",
      description: "Manage your conference schedule and participate effectively",
      icon: <MapPin className="h-6 w-6 text-purple-600" />,
      href: "/dashboard/conference",
    },
    {
      title: "Network",
      description: "Connect with other delegates and build your MUN network",
      icon: <Users className="h-6 w-6 text-pink-600" />,
      href: "/dashboard/network",
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Welcome, {user?.email?.split('@')[0] || 'Delegate'}!</h1>
        <p className="text-muted-foreground mt-2">
          Get started with MUN Connect&apos;s AI-powered tools
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {features.map((feature, index) => (
          <Card key={index} className="border-2 hover:border-blue-200 dark:hover:border-blue-800 transition-all duration-300">
            <CardHeader>
              <div className="mb-3">{feature.icon}</div>
              <CardTitle>{feature.title}</CardTitle>
              <CardDescription>{feature.description}</CardDescription>
            </CardHeader>
            <CardFooter>
              <Button
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                onClick={() => router.push(feature.href)}
              >
                Get Started
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      <Card className="mt-6 border-2 border-blue-100 dark:border-blue-900 bg-gradient-to-r from-blue-50/50 to-indigo-50/50 dark:from-blue-950/30 dark:to-indigo-950/30">
        <CardHeader>
          <CardTitle>Complete Your Profile</CardTitle>
          <CardDescription>
            Enhance your MUN Connect experience by completing your profile
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Add your bio, upload a profile picture, and share your MUN experience to connect with other delegates effectively.
          </p>
        </CardContent>
        <CardFooter>
          <Button
            variant="outline"
            className="w-full border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900"
            onClick={() => router.push('/dashboard/profile')}
          >
            Update Profile
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}

