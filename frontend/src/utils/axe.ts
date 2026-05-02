import React from 'react'
import ReactDOM from 'react-dom/client'

export async function runAxe() {
  if (!import.meta.env.DEV) return
  try {
    const axe = await import('@axe-core/react')
    axe.default(React, ReactDOM, 1000)
  } catch {
    // axe-core/react is dev-only; ignore if not installed
  }
}
