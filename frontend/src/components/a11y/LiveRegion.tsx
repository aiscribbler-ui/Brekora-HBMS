interface LiveRegionProps {
  message: string
  priority?: 'polite' | 'assertive'
}

export default function LiveRegion({ message, priority = 'polite' }: LiveRegionProps) {
  return (
    <div
      aria-live={priority}
      aria-atomic="true"
      className="sr-only"
      data-testid="live-region"
    >
      {message}
    </div>
  )
}
