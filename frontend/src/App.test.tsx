import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import App from '@/App'

const router = createMemoryRouter(
  [
    {
      path: '/',
      element: <App />,
      children: [
        {
          index: true,
          element: <div>Home</div>,
        },
      ],
    },
  ],
  { initialEntries: ['/'] },
)

describe('App', () => {
  it('renders the app shell', () => {
    render(<RouterProvider router={router} />)
    expect(screen.getByText('Brekora BMS')).toBeInTheDocument()
  })
})
