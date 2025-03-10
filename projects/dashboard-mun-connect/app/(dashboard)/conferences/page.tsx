"use client"

import React from "react"
import { useRouter } from "next/navigation"
import { Button } from "../../../components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../../components/ui/card"
import { CalendarDays, ArrowLeft } from "lucide-react"

export default function ConferencesPage() {
  const router = useRouter()

  return (
    <div className="container mx-auto py-10">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          My Conferences
        </h1>
        <Button 
          variant="outline" 
          onClick={() => router.back()}
          className="flex items-center"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Profile
        </Button>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Manage Your Conferences</CardTitle>
          <CardDescription>
            This page is under construction. In the future, you'll be able to add, edit, and track your conference experiences here.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-center p-12">
          <div className="text-center">
            <CalendarDays className="mx-auto h-12 w-12 text-blue-600 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Coming Soon</h3>
            <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
              We're working on this feature to help you better manage your conference experiences. 
              Check back soon for updates!
            </p>
          </div>
        </CardContent>
        <CardFooter className="flex justify-center">
          <Button onClick={() => router.back()}>
            Return to Profile
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
} 