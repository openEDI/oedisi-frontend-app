import { afterEach, describe, expect, it, vi } from 'vitest'
import { auth } from './auth'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('workspace authentication client', () => {
  it('sends Basic credentials only to the login endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ authenticated: true, username: 'alice' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(auth.login('alice', 'secret')).resolves.toEqual({
      authenticated: true,
      username: 'alice',
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/auth/login',
      expect.objectContaining({
        method: 'POST',
        credentials: 'same-origin',
        headers: { Authorization: `Basic ${btoa('alice:secret')}` },
      })
    )
  })

  it('treats an unauthorized status response as signed out', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('', { status: 401 }))
    )

    await expect(auth.status()).resolves.toEqual({ authenticated: false })
  })

  it('provides a clear rate-limit message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('', { status: 429 }))
    )

    await expect(auth.login('alice', 'wrong')).rejects.toThrow(
      'Too many sign-in attempts'
    )
  })
})
