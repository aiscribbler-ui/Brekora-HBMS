export const ROLES = {
  Admin: 'Admin',
  Manager: 'Manager',
  Owner: 'Owner',
  Guest: 'Guest',
} as const

export type Role = (typeof ROLES)[keyof typeof ROLES]

const KNOWN_ROLES = new Set<string>(Object.values(ROLES))

export function normaliseRole(value: string | null | undefined): Role | null {
  if (!value) return null
  const trimmed = value.trim()
  if (!trimmed) return null
  const titled = trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase()
  return KNOWN_ROLES.has(titled) ? (titled as Role) : null
}

export function hasRole(userRole: string | null | undefined, allowed: readonly Role[]): boolean {
  const role = normaliseRole(userRole)
  return role !== null && allowed.includes(role)
}

export function defaultRouteForRole(role: Role | null): string {
  switch (role) {
    case 'Admin':
      return '/admin'
    case 'Owner':
      return '/owner'
    case 'Guest':
      return '/guest'
    case 'Manager':
    default:
      return '/dashboard'
  }
}
