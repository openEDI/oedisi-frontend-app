export interface AuthStatus {
  authenticated: boolean
  username?: string
}

function basicAuthorization(username: string, password: string): string {
  const bytes = new TextEncoder().encode(`${username}:${password}`)
  let binary = ''
  for (const byte of bytes) {
    binary += String.fromCharCode(byte)
  }
  return `Basic ${btoa(binary)}`
}

async function authResponse(response: Response): Promise<AuthStatus> {
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    let message =
      typeof body.detail === 'string' ? body.detail : 'Unable to sign in'
    if (response.status === 401) {
      message = 'Invalid username or password'
    } else if (response.status === 429) {
      message = 'Too many sign-in attempts. Please wait a minute and try again.'
    } else if (response.status >= 500) {
      message =
        'The workspace is temporarily unavailable. Please try again shortly.'
    }
    throw new Error(message)
  }
  return body as AuthStatus
}

export const auth = {
  async status(): Promise<AuthStatus> {
    const response = await fetch('/auth/status', {
      credentials: 'same-origin',
      cache: 'no-store',
    })
    if (response.status === 401) {
      return { authenticated: false }
    }
    return authResponse(response)
  },

  async login(username: string, password: string): Promise<AuthStatus> {
    const response = await fetch('/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        Authorization: basicAuthorization(username, password),
      },
    })
    return authResponse(response)
  },

  async logout(): Promise<void> {
    const response = await fetch('/auth/logout', {
      method: 'POST',
      credentials: 'same-origin',
    })
    if (!response.ok) {
      throw new Error('Unable to sign out')
    }
  },
}
