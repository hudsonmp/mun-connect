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
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { detailLevels } from "@/lib/writing-styles"

export interface DetailLevelSelectProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
}

export function DetailLevelSelect({
  value,
  onChange,
  disabled = false,
  placeholder = "Select detail level",
}: DetailLevelSelectProps) {
  const [open, setOpen] = React.useState(false)
  
  const selectedLevel = detailLevels.find(level => level.id === value)

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
          {selectedLevel ? selectedLevel.name : placeholder}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0">
        <Command>
          <CommandInput placeholder="Search detail levels..." />
          <CommandEmpty>No detail level found.</CommandEmpty>
          <CommandGroup className="max-h-[300px] overflow-y-auto">
            {detailLevels.map((level) => (
              <CommandItem
                key={level.id}
                value={level.id}
                onSelect={() => {
                  onChange(level.id)
                  setOpen(false)
                }}
              >
                <Check
                  className={cn(
                    "mr-2 h-4 w-4",
                    value === level.id ? "opacity-100" : "opacity-0"
                  )}
                />
                <div className="flex flex-col">
                  <span>{level.name}</span>
                  <span className="text-xs text-muted-foreground">{level.description}</span>
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  )
}