"use client"

import { motion } from "framer-motion"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Calendar, FileText, MessageSquare, Users } from "lucide-react"

// Sample data
const upcomingConferences = [
  {
    id: 1,
    name: "Harvard Model United Nations",
    acronym: "HMUN",
    date: "January 26-29, 2024",
    location: "Boston, MA",
    committee: "UN Security Council",
    country: "United States",
    status: "Confirmed",
  },
  {
    id: 2,
    name: "National Model United Nations",
    acronym: "NMUN",
    date: "March 24-28, 2024",
    location: "New York, NY",
    committee: "UN General Assembly",
    country: "France",
    status: "Pending",
  },
]

const pastConferences = [
  {
    id: 3,
    name: "World Federation Model United Nations",
    acronym: "WFMUN",
    date: "October 15-18, 2023",
    location: "London, UK",
    committee: "UN Human Rights Council",
    country: "Japan",
    status: "Completed",
  },
]

const documents = [
  {
    id: 1,
    title: "Climate Change Position Paper",
    type: "Position Paper",
    conference: "HMUN 2024",
    lastEdited: "2 days ago",
    status: "Draft",
  },
  {
    id: 2,
    title: "Opening Speech on Nuclear Disarmament",
    type: "Speech",
    conference: "NMUN 2024",
    lastEdited: "1 week ago",
    status: "Completed",
  },
  {
    id: 3,
    title: "Resolution on Sustainable Development",
    type: "Resolution",
    conference: "WFMUN 2023",
    lastEdited: "2 months ago",
    status: "Submitted",
  },
]

export function DashboardOverview() {
  return (
    <div className="space-y-8">
      <div className="flex flex-col space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Welcome back! Here's an overview of your MUN activities.</p>
      </div>

      <Tabs defaultValue="upcoming" className="space-y-4">
        <TabsList>
          <TabsTrigger value="upcoming">Upcoming</TabsTrigger>
          <TabsTrigger value="past">Past</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
        </TabsList>

        <TabsContent value="upcoming" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2">
            {upcomingConferences.map((conference) => (
              <motion.div
                key={conference.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <div className="space-y-1">
                      <CardTitle className="text-xl">{conference.acronym}</CardTitle>
                      <CardDescription>{conference.name}</CardDescription>
                    </div>
                    <Badge variant={conference.status === "Confirmed" ? "default" : "outline"}>
                      {conference.status}
                    </Badge>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-2">
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{conference.date}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{conference.committee}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">Representing:</span>
                        <span className="text-sm">{conference.country}</span>
                      </div>
                    </div>
                  </CardContent>
                  <CardFooter>
                    <Button variant="outline" className="w-full">
                      View Details
                    </Button>
                  </CardFooter>
                </Card>
              </motion.div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="past" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2">
            {pastConferences.map((conference) => (
              <motion.div
                key={conference.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <div className="space-y-1">
                      <CardTitle className="text-xl">{conference.acronym}</CardTitle>
                      <CardDescription>{conference.name}</CardDescription>
                    </div>
                    <Badge variant="secondary">{conference.status}</Badge>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-2">
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{conference.date}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{conference.committee}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">Represented:</span>
                        <span className="text-sm">{conference.country}</span>
                      </div>
                    </div>
                  </CardContent>
                  <CardFooter>
                    <Button variant="outline" className="w-full">
                      View Summary
                    </Button>
                  </CardFooter>
                </Card>
              </motion.div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="documents" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {documents.map((document) => (
              <motion.div
                key={document.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <div className="space-y-1">
                      <CardTitle className="text-lg">{document.title}</CardTitle>
                      <CardDescription>{document.conference}</CardDescription>
                    </div>
                    {document.type === "Position Paper" ? (
                      <FileText className="h-5 w-5 text-blue-500" />
                    ) : document.type === "Speech" ? (
                      <MessageSquare className="h-5 w-5 text-indigo-500" />
                    ) : (
                      <Users className="h-5 w-5 text-purple-500" />
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Type:</span>
                        <span className="text-sm">{document.type}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Last Edited:</span>
                        <span className="text-sm">{document.lastEdited}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">Status:</span>
                        <Badge
                          variant={
                            document.status === "Draft"
                              ? "outline"
                              : document.status === "Completed"
                                ? "default"
                                : "secondary"
                          }
                        >
                          {document.status}
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                  <CardFooter>
                    <Button variant="outline" className="w-full">
                      Edit Document
                    </Button>
                  </CardFooter>
                </Card>
              </motion.div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

