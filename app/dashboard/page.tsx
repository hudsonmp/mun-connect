import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Calendar, MapPin, Users } from "lucide-react"

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

const currentConferences = [
  {
    id: 3,
    name: "World Federation Model United Nations",
    acronym: "WFMUN",
    date: "In Progress (Ends May 15, 2024)",
    location: "London, UK",
    committee: "UN Human Rights Council",
    country: "Japan",
    status: "Active",
  },
]

const pastConferences = [
  {
    id: 4,
    name: "Yale Model United Nations",
    acronym: "YMUN",
    date: "October 15-18, 2023",
    location: "New Haven, CT",
    committee: "UN Economic and Social Council",
    country: "Germany",
    status: "Completed",
  },
  {
    id: 5,
    name: "Berkeley Model United Nations",
    acronym: "BMUN",
    date: "August 5-8, 2023",
    location: "Berkeley, CA",
    committee: "World Health Organization",
    country: "Brazil",
    status: "Completed",
  },
]

export default function DashboardPage() {
  return (
    <div className="space-y-4 sm:space-y-6 w-full max-w-full">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          Dashboard
        </h1>
        <p className="text-sm sm:text-base text-muted-foreground mt-2">
          Welcome back! Here's an overview of your committee assignments.
        </p>
      </div>

      <Tabs defaultValue="upcoming" className="space-y-4 w-full">
        <TabsList className="bg-blue-100/50 dark:bg-blue-900/20 w-full sm:w-auto flex">
          <TabsTrigger value="upcoming" className="flex-1 sm:flex-initial">
            Upcoming
          </TabsTrigger>
          <TabsTrigger value="current" className="flex-1 sm:flex-initial">
            Current
          </TabsTrigger>
          <TabsTrigger value="past" className="flex-1 sm:flex-initial">
            Past
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upcoming" className="space-y-4">
          {upcomingConferences.length === 0 ? (
            <Card className="border-blue-200 dark:border-blue-800">
              <CardContent className="py-10 text-center">
                <p className="text-muted-foreground">No upcoming conferences</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {upcomingConferences.map((conference) => (
                <Card
                  key={conference.id}
                  className="overflow-hidden border-blue-200 dark:border-blue-800 hover:shadow-md transition-all"
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-indigo-500/10 pointer-events-none" />
                  <CardHeader className="pb-2 relative">
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg sm:text-xl bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                          {conference.acronym}
                        </CardTitle>
                        <CardDescription>{conference.name}</CardDescription>
                      </div>
                      <Badge
                        variant={conference.status === "Confirmed" ? "default" : "outline"}
                        className={
                          conference.status === "Confirmed" ? "bg-gradient-to-r from-blue-600 to-indigo-600" : ""
                        }
                      >
                        {conference.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="relative">
                    <div className="space-y-2">
                      <div className="flex items-center text-xs sm:text-sm">
                        <Calendar className="mr-2 h-4 w-4 text-blue-500 flex-shrink-0" />
                        <span className="truncate">{conference.date}</span>
                      </div>
                      <div className="flex items-center text-xs sm:text-sm">
                        <MapPin className="mr-2 h-4 w-4 text-blue-500 flex-shrink-0" />
                        <span className="truncate">{conference.location}</span>
                      </div>
                      <div className="flex items-center text-xs sm:text-sm">
                        <Users className="mr-2 h-4 w-4 text-blue-500 flex-shrink-0" />
                        <span className="truncate">{conference.committee}</span>
                      </div>
                      <div className="pt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20"
                        >
                          View Details
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="current" className="space-y-4">
          {currentConferences.length === 0 ? (
            <Card className="border-blue-200 dark:border-blue-800">
              <CardContent className="py-10 text-center">
                <p className="text-muted-foreground">No current conferences</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {currentConferences.map((conference) => (
                <Card
                  key={conference.id}
                  className="overflow-hidden border-blue-200 dark:border-blue-800 hover:shadow-md transition-all"
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-green-500/5 to-blue-500/10 pointer-events-none" />
                  <CardHeader className="pb-2 relative">
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg sm:text-xl bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                          {conference.acronym}
                        </CardTitle>
                        <CardDescription>{conference.name}</CardDescription>
                      </div>
                      <Badge variant="default" className="bg-gradient-to-r from-green-500 to-blue-500">
                        {conference.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="relative">
                    <div className="space-y-2">
                      <div className="flex items-center text-xs sm:text-sm">
                        <Calendar className="mr-2 h-4 w-4 text-blue-500 flex-shrink-0" />
                        <span className="truncate">{conference.date}</span>
                      </div>
                      <div className="flex items-center text-xs sm:text-sm">
                        <MapPin className="mr-2 h-4 w-4 text-blue-500 flex-shrink-0" />
                        <span className="truncate">{conference.location}</span>
                      </div>
                      <div className="flex items-center text-xs sm:text-sm">
                        <Users className="mr-2 h-4 w-4 text-blue-500 flex-shrink-0" />
                        <span className="truncate">{conference.committee}</span>
                      </div>
                      <div className="pt-2">
                        <Button
                          size="sm"
                          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                        >
                          Enter Conference
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="past" className="space-y-4">
          {pastConferences.length === 0 ? (
            <Card className="border-blue-200 dark:border-blue-800">
              <CardContent className="py-10 text-center">
                <p className="text-muted-foreground">No past conferences</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {pastConferences.map((conference) => (
                <Card
                  key={conference.id}
                  className="overflow-hidden border-blue-200 dark:border-blue-800 hover:shadow-md transition-all"
                >
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 pointer-events-none" />
                  <CardHeader className="pb-2 relative">
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg sm:text-xl bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                          {conference.acronym}
                        </CardTitle>
                        <CardDescription>{conference.name}</CardDescription>
                      </div>
                      <Badge
                        variant="secondary"
                        className="bg-gradient-to-r from-blue-100 to-indigo-100 text-blue-700 dark:from-blue-900/40 dark:to-indigo-900/40 dark:text-blue-300"
                      >
                        {conference.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="relative">
                    <div className="space-y-2">
                      <div className="flex items-center text-xs sm:text-sm">
                        <Calendar className="mr-2 h-4 w-4 text-blue-500 flex-shrink-0" />
                        <span className="truncate">{conference.date}</span>
                      </div>
                      <div className="flex items-center text-xs sm:text-sm">
                        <MapPin className="mr-2 h-4 w-4 text-blue-500 flex-shrink-0" />
                        <span className="truncate">{conference.location}</span>
                      </div>
                      <div className="flex items-center text-xs sm:text-sm">
                        <Users className="mr-2 h-4 w-4 text-blue-500 flex-shrink-0" />
                        <span className="truncate">{conference.committee}</span>
                      </div>
                      <div className="pt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20"
                        >
                          View Summary
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

