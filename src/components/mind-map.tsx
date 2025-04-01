"use client"

import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { ChevronRight, ChevronDown } from 'lucide-react'

interface SubtopicType {
  name: string
  key_points: string[]
  relevant_actors?: string[]
}

interface MindMapData {
  topic: string
  subtopics: SubtopicType[]
  key_issues: string[]
  historical_context: string[]
  potential_solutions: string[]
  countries_mentioned: string[]
  [key: string]: any // For any additional fields
}

interface MindMapProps {
  data: MindMapData
}

export function MindMap({ data }: MindMapProps) {
  const [expandedSections, setExpandedSections] = React.useState<{[key: string]: boolean}>({
    subtopics: true,
    key_issues: true,
    historical_context: true,
    potential_solutions: true,
    countries_mentioned: true,
  })
  
  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }
  
  if (!data) {
    return <div className="text-center py-4">No mind map data available</div>
  }
  
  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-lg font-semibold">{data.topic}</h2>
      </div>
      
      {/* Key Issues Section */}
      <Collapsible
        open={expandedSections.key_issues}
        onOpenChange={() => toggleSection('key_issues')}
        className="border rounded-md overflow-hidden"
      >
        <CollapsibleTrigger className="flex items-center justify-between w-full p-3 bg-muted/50 hover:bg-muted/80 transition-colors">
          <h3 className="font-medium">Key Issues</h3>
          {expandedSections.key_issues ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="p-3">
            {data.key_issues && data.key_issues.length > 0 ? (
              <ul className="list-disc pl-5 space-y-1">
                {data.key_issues.map((issue, index) => (
                  <li key={index} className="text-sm">{issue}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No key issues available</p>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
      
      {/* Subtopics Section */}
      <Collapsible
        open={expandedSections.subtopics}
        onOpenChange={() => toggleSection('subtopics')}
        className="border rounded-md overflow-hidden"
      >
        <CollapsibleTrigger className="flex items-center justify-between w-full p-3 bg-muted/50 hover:bg-muted/80 transition-colors">
          <h3 className="font-medium">Subtopics</h3>
          {expandedSections.subtopics ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="p-3 space-y-3">
            {data.subtopics && data.subtopics.length > 0 ? (
              data.subtopics.map((subtopic, index) => (
                <Card key={index} className="overflow-hidden">
                  <CardContent className="p-3">
                    <h4 className="font-medium text-sm">{subtopic.name}</h4>
                    {subtopic.key_points && subtopic.key_points.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-muted-foreground mb-1">Key Points:</p>
                        <ul className="list-disc pl-5 space-y-1">
                          {subtopic.key_points.map((point, i) => (
                            <li key={i} className="text-xs">{point}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {subtopic.relevant_actors && subtopic.relevant_actors.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-muted-foreground mb-1">Relevant Actors:</p>
                        <div className="flex flex-wrap gap-1">
                          {subtopic.relevant_actors.map((actor, i) => (
                            <Badge key={i} variant="outline" className="text-xs">{actor}</Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No subtopics available</p>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
      
      {/* Historical Context Section */}
      <Collapsible
        open={expandedSections.historical_context}
        onOpenChange={() => toggleSection('historical_context')}
        className="border rounded-md overflow-hidden"
      >
        <CollapsibleTrigger className="flex items-center justify-between w-full p-3 bg-muted/50 hover:bg-muted/80 transition-colors">
          <h3 className="font-medium">Historical Context</h3>
          {expandedSections.historical_context ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="p-3">
            {data.historical_context && data.historical_context.length > 0 ? (
              <ul className="list-disc pl-5 space-y-1">
                {data.historical_context.map((item, index) => (
                  <li key={index} className="text-sm">{item}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No historical context available</p>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
      
      {/* Potential Solutions Section */}
      <Collapsible
        open={expandedSections.potential_solutions}
        onOpenChange={() => toggleSection('potential_solutions')}
        className="border rounded-md overflow-hidden"
      >
        <CollapsibleTrigger className="flex items-center justify-between w-full p-3 bg-muted/50 hover:bg-muted/80 transition-colors">
          <h3 className="font-medium">Potential Solutions</h3>
          {expandedSections.potential_solutions ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="p-3">
            {data.potential_solutions && data.potential_solutions.length > 0 ? (
              <ul className="list-disc pl-5 space-y-1">
                {data.potential_solutions.map((solution, index) => (
                  <li key={index} className="text-sm">{solution}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No potential solutions available</p>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
      
      {/* Countries Mentioned Section */}
      <Collapsible
        open={expandedSections.countries_mentioned}
        onOpenChange={() => toggleSection('countries_mentioned')}
        className="border rounded-md overflow-hidden"
      >
        <CollapsibleTrigger className="flex items-center justify-between w-full p-3 bg-muted/50 hover:bg-muted/80 transition-colors">
          <h3 className="font-medium">Countries Mentioned</h3>
          {expandedSections.countries_mentioned ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="p-3">
            {data.countries_mentioned && data.countries_mentioned.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {data.countries_mentioned.map((country, index) => (
                  <Badge key={index} variant="outline">{country}</Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No countries mentioned</p>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
} 