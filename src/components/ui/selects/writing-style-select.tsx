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
import { writingStyles } from "@/lib/writing-styles"
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger 
} from "@/components/ui/tooltip"
import { Badge } from "@/components/ui/badge"
import { InfoIcon } from "lucide-react"

export interface WritingStyleSelectProps {
  value: string
  onChange: (value: string) => void
  disabled?: boolean
  placeholder?: string
  showTooltip?: boolean
}

export function WritingStyleSelect({
  value,
  onChange,
  disabled = false,
  placeholder = "Select a writing style",
  showTooltip = true,
}: WritingStyleSelectProps) {
  const [open, setOpen] = React.useState(false)
  
  const selectedStyle = writingStyles.find(style => style.id === value)

  return (
    <div className="space-y-1">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className="w-full justify-between"
          >
            {selectedStyle ? selectedStyle.name : placeholder}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-full p-0">
          <Command>
            <CommandInput placeholder="Search writing styles..." />
            <CommandEmpty>No writing style found.</CommandEmpty>
            <CommandGroup className="max-h-[300px] overflow-y-auto">
              {writingStyles.map((style) => (
                <CommandItem
                  key={style.id}
                  value={style.id}
                  onSelect={() => {
                    onChange(style.id)
                    setOpen(false)
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-4 w-4",
                      value === style.id ? "opacity-100" : "opacity-0"
                    )}
                  />
                  <div className="flex flex-col">
                    <span>{style.name}</span>
                    <span className="text-xs text-muted-foreground">{style.description}</span>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </Command>
        </PopoverContent>
      </Popover>
      
      {selectedStyle && showTooltip && (
        <div className="mt-2">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-sm font-medium">Characteristics</h4>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <InfoIcon className="h-4 w-4 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="w-[250px] text-sm">Common features of the {selectedStyle.name.toLowerCase()} writing style</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <div className="flex flex-wrap gap-1">
            {selectedStyle.characteristics.map((characteristic, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {characteristic}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  )
} 