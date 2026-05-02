export default function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 z-50 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-md shadow-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
    >
      Skip to content
    </a>
  )
}
