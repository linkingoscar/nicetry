import { useEffect, useState } from 'react'
import { CheckIcon, AlertCircleIcon } from './Icons'

export type ToastType = 'success' | 'error' | 'info'

export interface ToastItem {
  id: string
  message: string
  type: ToastType
  duration?: number
}

type ToastListener = (toasts: ToastItem[]) => void

let toastsState: ToastItem[] = []
const listeners = new Set<ToastListener>()

export function showToast(message: string, type: ToastType = 'success', duration = 3200) {
  const id = Math.random().toString(36).substring(2, 9)
  const item: ToastItem = { id, message, type, duration }
  toastsState = [...toastsState, item]
  listeners.forEach((listener) => {
    listener(toastsState)
  })

  setTimeout(() => {
    toastsState = toastsState.filter((t) => t.id !== id)
    listeners.forEach((listener) => {
      listener(toastsState)
    })
  }, duration)
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>(toastsState)

  useEffect(() => {
    listeners.add(setToasts)
    return () => {
      listeners.delete(setToasts)
    }
  }, [])

  if (toasts.length === 0) return null

  return (
    <section className="toast-container" aria-label="通知提示">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast-item toast-${toast.type}`}>
          <span className="toast-icon">
            {toast.type === 'error' ? (
              <AlertCircleIcon size={16} />
            ) : (
              <CheckIcon size={16} />
            )}
          </span>
          <span className="toast-message">{toast.message}</span>
        </div>
      ))}
    </section>
  )
}
