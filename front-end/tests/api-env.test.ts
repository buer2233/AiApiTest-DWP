import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

import { resolveApiTimeoutMs } from '../src/api/env'

describe('api client environment config', () => {
  it('resolves request timeout from VITE_API_TIMEOUT_MS', () => {
    expect(resolveApiTimeoutMs('15000')).toBe(15000)
    expect(resolveApiTimeoutMs('0')).toBe(10000)
    expect(resolveApiTimeoutMs('not-a-number')).toBe(10000)
  })

  it('wires VITE_API_TIMEOUT_MS into the Axios client', () => {
    const clientSource = readFileSync(resolve(__dirname, '../src/api/client.ts'), 'utf-8')

    expect(clientSource).toContain('resolveApiTimeoutMs(import.meta.env.VITE_API_TIMEOUT_MS)')
    expect(clientSource).not.toContain('timeout: 10000')
  })
})
