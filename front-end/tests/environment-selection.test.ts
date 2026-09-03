import { describe, expect, it } from 'vitest'

import { resolveEnvironmentId } from '@/utils/environment-selection'

describe('resolveEnvironmentId', () => {
  const environments = [{ id: 2 }, { id: 3 }]

  it('keeps an active requested environment', () => {
    expect(resolveEnvironmentId('3', environments)).toBe('3')
  })

  it('falls back to the first active environment for a stale id', () => {
    expect(resolveEnvironmentId('1', environments)).toBe('2')
  })
})
