"use client"

import * as React from "react"
import { Check, ChevronsUpDown } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import topics from "@/lib/topics"

export interface TopicSelectProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
  category?: keyof typeof topics | "all" 
}

export function TopicSelect({
  value,
  onChange,
  disabled = false,
  placeholder = "Select a topic",
  category = "all",
}: TopicSelectProps) {
  const [open, setOpen] = React.useState(false)

  // Create a flat list of topics if needed
  const allTopics = React.useMemo(() => {
    if (category === "all") {
      return Object.values(topics).flat();
    }
    return topics[category];
  }, [category]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className="w-full justify-between"
        >
          {value ? value : placeholder}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0">
        <Command>
          <CommandInput placeholder="Search topics..." />
          <CommandEmpty>No topic found.</CommandEmpty>
          <CommandList className="max-h-[300px] overflow-y-auto">
            {category === "all" ? (
              <>
                {Object.entries(topics).map(([categoryName, categoryTopics]) => (
                  <React.Fragment key={categoryName}>
                    <CommandGroup heading={formatCategoryName(categoryName)}>
                      {categoryTopics.map((topic) => (
                        <CommandItem
                          key={topic}
                          value={topic}
                          onSelect={() => {
                            onChange(topic)
                            setOpen(false)
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              value === topic ? "opacity-100" : "opacity-0"
                            )}
                          />
                          {topic}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                    <CommandSeparator />
                  </React.Fragment>
                ))}
              </>
            ) : (
              <CommandGroup>
                {allTopics.map((topic) => (
                  <CommandItem
                    key={topic}
                    value={topic}
                    onSelect={() => {
                      onChange(topic)
                      setOpen(false)
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value === topic ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {topic}
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

// Helper function to format category names
const formatCategoryName = (category: string): string => {
  const words = category.replace(/([A-Z])/g, ' $1').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
} 