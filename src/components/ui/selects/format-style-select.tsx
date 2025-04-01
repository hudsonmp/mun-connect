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
import { formatStyles } from "@/lib/writing-styles"

export interface FormatStyleSelectProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
}

export function FormatStyleSelect({
  value,
  onChange,
  disabled = false,
  placeholder = "Select format style",
}: FormatStyleSelectProps) {
  const [open, setOpen] = React.useState(false)
  
  const selectedFormat = formatStyles.find(format => format.id === value)

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
          {selectedFormat ? selectedFormat.name : placeholder}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0">
        <Command>
          <CommandInput placeholder="Search format styles..." />
          <CommandEmpty>No format style found.</CommandEmpty>
          <CommandGroup className="max-h-[300px] overflow-y-auto">
            {formatStyles.map((format) => (
              <CommandItem
                key={format.id}
                value={format.id}
                onSelect={() => {
                  onChange(format.id)
                  setOpen(false)
                }}
              >
                <Check
                  className={cn(
                    "mr-2 h-4 w-4",
                    value === format.id ? "opacity-100" : "opacity-0"
                  )}
                />
                <div className="flex flex-col">
                  <span>{format.name}</span>
                  <span className="text-xs text-muted-foreground">{format.description}</span>
                </div>
              </CommandItem>
            ))}
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  )
} 