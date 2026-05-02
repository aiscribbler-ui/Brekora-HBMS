import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import SkipLink from './SkipLink'
import LiveRegion from './LiveRegion'

describe('SkipLink', () => {
  it('renders and links to #main-content', () => {
    render(<SkipLink />)
    const link = screen.getByText('Skip to content')
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '#main-content')
  })
})

describe('LiveRegion', () => {
  it('announces with aria-live="polite" by default', () => {
    render(<LiveRegion message="Form saved" />)
    const region = screen.getByTestId('live-region')
    expect(region).toHaveAttribute('aria-live', 'polite')
    expect(region).toHaveTextContent('Form saved')
  })

  it('announces with aria-live="assertive" when priority is assertive', () => {
    render(<LiveRegion message="Error occurred" priority="assertive" />)
    const region = screen.getByTestId('live-region')
    expect(region).toHaveAttribute('aria-live', 'assertive')
    expect(region).toHaveTextContent('Error occurred')
  })
})

describe('Accessible form pattern', () => {
  it('input has aria-describedby linked to error message', () => {
    render(
      <div>
        <label htmlFor="email">Email</label>
        <input
          id="email"
          type="email"
          aria-invalid="true"
          aria-describedby="email-error"
        />
        <p id="email-error">Invalid email address</p>
      </div>,
    )
    const input = screen.getByLabelText('Email')
    expect(input).toHaveAttribute('aria-describedby', 'email-error')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('Invalid email address')).toHaveAttribute('id', 'email-error')
  })
})
