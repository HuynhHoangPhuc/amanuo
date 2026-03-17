/** Global command palette (⌘K) — search and navigate pages, run actions. */

import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from '@tanstack/react-router'
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from '#/components/ui/command'
import { ALL_NAV_GROUPS } from './sidebar-nav'

/** Page-level keyboard shortcuts for quick navigation. */
/** Page shortcuts — avoid ⌘S (browser save) and ⌘D (browser bookmark). */
const PAGE_SHORTCUTS: Record<string, string> = {
  j: '/jobs',
  b: '/batches',
}

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      /* Ignore when typing in inputs */
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement).isContentEditable) return

      /* ⌘K / Ctrl+K → open palette */
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((o) => !o)
        return
      }

      /* Page shortcuts: ⌘D, ⌘J, ⌘B, ⌘S */
      if (e.metaKey || e.ctrlKey) {
        const route = PAGE_SHORTCUTS[e.key]
        if (route) {
          e.preventDefault()
          navigate({ to: route })
        }
      }
    },
    [navigate],
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  function navigateTo(to: string) {
    navigate({ to })
    setOpen(false)
  }

  function toggleTheme() {
    const btn = document.querySelector<HTMLButtonElement>('[aria-label*="mode"]')
    btn?.click()
    setOpen(false)
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." className="text-[13px]" />
      <CommandList className="max-h-[360px]">
        <CommandEmpty>No results found.</CommandEmpty>

        {ALL_NAV_GROUPS.map((group) => (
          <CommandGroup key={group.label} heading={group.label}>
            {group.items.map((item) => {
              const Icon = item.icon
              return (
                <CommandItem
                  key={item.to}
                  value={item.label}
                  onSelect={() => navigateTo(item.to)}
                  className="text-[13px]"
                >
                  <span className="mr-2 text-muted-foreground">
                    <Icon size={16} strokeWidth={1.5} />
                  </span>
                  <span className="flex-1">{item.label}</span>
                  {item.kbd && (
                    <kbd className="text-[11px] font-mono text-muted-foreground/50">{item.kbd}</kbd>
                  )}
                </CommandItem>
              )
            })}
          </CommandGroup>
        ))}

        <CommandGroup heading="Actions">
          <CommandItem value="Toggle theme" onSelect={toggleTheme} className="text-[13px]">
            <span>Toggle theme</span>
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
