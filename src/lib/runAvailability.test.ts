import { afterEach, describe, expect, it, vi } from 'vitest'

import { createRunAvailabilityController } from './runAvailability'

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('run availability controller', () => {
  it('records busy and available responses', async () => {
    const check = vi
      .fn()
      .mockResolvedValueOnce({ available: false, retry_after_seconds: 5 })
      .mockResolvedValueOnce({ available: true, retry_after_seconds: 5 })
    const controller = createRunAvailabilityController(check)

    await controller.refresh()
    expect(controller.available.value).toBe(false)
    await controller.refresh()
    expect(controller.available.value).toBe(true)
  })

  it('fails open when the availability request fails', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const controller = createRunAvailabilityController(() =>
      Promise.reject(new Error('network failure')),
    )
    controller.markBusy()

    await controller.refresh()
    expect(controller.available.value).toBeNull()
  })

  it('polls every five seconds and stops cleanly', async () => {
    vi.useFakeTimers()
    const check = vi
      .fn()
      .mockResolvedValue({ available: true, retry_after_seconds: 5 })
    const controller = createRunAvailabilityController(check)

    controller.start()
    await vi.advanceTimersByTimeAsync(0)
    expect(check).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(5000)
    expect(check).toHaveBeenCalledTimes(2)
    controller.stop()
    await vi.advanceTimersByTimeAsync(5000)
    expect(check).toHaveBeenCalledTimes(2)
  })

  it('can be marked busy immediately after a launch race', () => {
    const controller = createRunAvailabilityController(() =>
      Promise.resolve({ available: true, retry_after_seconds: 5 }),
    )
    controller.markBusy()
    expect(controller.available.value).toBe(false)
  })

  it('does not let a stale availability response overwrite a launch', async () => {
    let resolveCheck: ((value: { available: boolean; retry_after_seconds: number }) => void) | undefined
    const controller = createRunAvailabilityController(
      () =>
        new Promise((resolve) => {
          resolveCheck = resolve
        }),
    )

    const pendingRefresh = controller.refresh()
    controller.markBusy()
    resolveCheck?.({ available: true, retry_after_seconds: 5 })
    await pendingRefresh

    expect(controller.available.value).toBe(false)
  })
})
