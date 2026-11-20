import { ref } from 'vue'

import { api, type RunAvailability } from './api'

export const RUN_BUSY_MESSAGE =
  'Another simulation is currently running. Your simulation was not started. Please wait and try again.'

type AvailabilityCheck = () => Promise<RunAvailability>

export function createRunAvailabilityController(
  check: AvailabilityCheck = () => api.getRunAvailability(),
  intervalMilliseconds = 5000,
) {
  const available = ref<boolean | null>(null)
  let timer: ReturnType<typeof setInterval> | undefined
  let consumers = 0
  let stateVersion = 0

  const refresh = async () => {
    const requestVersion = stateVersion
    try {
      const response = await check()
      if (requestVersion === stateVersion) {
        available.value = response.available
      }
    } catch (error) {
      console.error('Failed to get simulation availability:', error)
      if (requestVersion === stateVersion) {
        available.value = null
      }
    }
  }

  const start = () => {
    consumers += 1
    if (timer !== undefined) return
    void refresh()
    timer = setInterval(() => void refresh(), intervalMilliseconds)
  }

  const stop = () => {
    consumers = Math.max(0, consumers - 1)
    if (consumers > 0) return
    if (timer === undefined) return
    clearInterval(timer)
    timer = undefined
  }

  const markBusy = () => {
    stateVersion += 1
    available.value = false
  }

  return { available, refresh, start, stop, markBusy }
}

export const runAvailability = createRunAvailabilityController()
