import * as ToastPrimitive from '@radix-ui/react-toast'
import { CheckCircle2, Info, XCircle } from 'lucide-react'
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

import { cn } from '@/utils/cn'

type ToastTone = 'success' | 'error' | 'info'

interface ToastMessage {
  id: number
  title: string
  description?: string
  tone: ToastTone
}

interface ToastContextValue {
  toast: (message: Omit<ToastMessage, 'id'>) => void
  success: (title: string, description?: string) => void
  error: (title: string, description?: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const TONE_STYLES: Record<ToastTone, string> = {
  success: 'border-olive-300 bg-olive-50 text-olive-900',
  error: 'border-clay-300 bg-clay-50 text-clay-900',
  info: 'border-ink-100 bg-white text-ink-900',
}

const TONE_ICONS: Record<ToastTone, typeof CheckCircle2> = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([])

  const toast = useCallback((message: Omit<ToastMessage, 'id'>) => {
    setMessages((current) => [...current, { ...message, id: Date.now() + Math.random() }])
  }, [])

  const value = useMemo<ToastContextValue>(
    () => ({
      toast,
      success: (title, description) => toast({ title, description, tone: 'success' }),
      error: (title, description) => toast({ title, description, tone: 'error' }),
    }),
    [toast],
  )

  return (
    <ToastContext.Provider value={value}>
      <ToastPrimitive.Provider swipeDirection="right" duration={5000}>
        {children}
        {messages.map((message) => {
          const Icon = TONE_ICONS[message.tone]
          return (
            <ToastPrimitive.Root
              key={message.id}
              className={cn(
                'flex items-start gap-3 rounded-xl border-2 p-4 shadow-lift data-[state=closed]:animate-out data-[state=closed]:fade-out',
                TONE_STYLES[message.tone],
              )}
              onOpenChange={(open) => {
                if (!open) setMessages((current) => current.filter((m) => m.id !== message.id))
              }}
            >
              <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <ToastPrimitive.Title className="font-semibold">{message.title}</ToastPrimitive.Title>
                {message.description ? (
                  <ToastPrimitive.Description className="mt-0.5 text-sm opacity-90">
                    {message.description}
                  </ToastPrimitive.Description>
                ) : null}
              </div>
            </ToastPrimitive.Root>
          )
        })}
        <ToastPrimitive.Viewport className="fixed bottom-0 start-0 z-[100] flex w-full max-w-sm flex-col gap-2 p-4" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}
