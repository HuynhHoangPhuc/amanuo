/**
 * WebSocket client with automatic exponential-backoff reconnection.
 * Manages a single WS connection per page session.
 */

const WS_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(
  /^http/,
  'ws',
)

type EventHandler = (data: unknown) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectDelay = 1000
  private readonly maxDelay = 30_000
  private readonly listeners = new Map<string, Set<EventHandler>>()
  private apiKey = ''
  private stopped = false

  connect(apiKey: string): void {
    this.apiKey = apiKey
    this.stopped = false
    this._connect()
  }

  disconnect(): void {
    this.stopped = true
    this.ws?.close()
    this.ws = null
  }

  on(eventType: string, handler: EventHandler): void {
    if (!this.listeners.has(eventType)) this.listeners.set(eventType, new Set())
    this.listeners.get(eventType)!.add(handler)
  }

  off(eventType: string, handler: EventHandler): void {
    this.listeners.get(eventType)?.delete(handler)
  }

  private _connect(): void {
    if (this.stopped || !this.apiKey) return
    const url = `${WS_BASE}/ws/events?api_key=${encodeURIComponent(this.apiKey)}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.reconnectDelay = 1000
    }

    this.ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data as string) as { type: string; data: unknown }
        this.listeners.get(event.type)?.forEach((h) => h(event.data))
        this.listeners.get('*')?.forEach((h) => h(event))
      } catch {
        // ignore malformed frames
      }
    }

    this.ws.onclose = () => {
      if (!this.stopped) {
        setTimeout(() => this._connect(), this.reconnectDelay)
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxDelay)
      }
    }
  }
}

export const wsClient = new WebSocketClient()
