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
import committees from "@/lib/committees"

export interface CommitteeSelectProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
  category?: keyof typeof committees | "all" 
}

export function CommitteeSelect({
  value,
  onChange,
  disabled = false,
  placeholder = "Select a committee",
  category = "all",
}: CommitteeSelectProps) {
  const [open, setOpen] = React.useState(false)

  // Create a flat list of committees if needed
  const allCommittees = React.useMemo(() => {
    if (category === "all") {
      return Object.values(committees).flat();
    }
    return committees[category];
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
          <CommandInput placeholder="Search committees..." />
          <CommandEmpty>No committee found.</CommandEmpty>
          <CommandList className="max-h-[300px] overflow-y-auto">
            {category === "all" ? (
              <>
                {Object.entries(committees).map(([categoryName, categoryCommittees]) => (
                  <React.Fragment key={categoryName}>
                    <CommandGroup heading={formatCategoryName(categoryName)}>
                      {categoryCommittees.map((committee) => (
                        <CommandItem
                          key={committee}
                          value={committee}
                          onSelect={() => {
                            onChange(committee)
                            setOpen(false)
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              value === committee ? "opacity-100" : "opacity-0"
                            )}
                          />
                          {committee}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                    <CommandSeparator />
                  </React.Fragment>
                ))}
              </>
            ) : (
              <CommandGroup>
                {allCommittees.map((committee) => (
                  <CommandItem
                    key={committee}
                    value={committee}
                    onSelect={() => {
                      onChange(committee)
                      setOpen(false)
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        value === committee ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {committee}
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