import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

import { API_BASE_PATH, API_TIMEOUT_MS } from '../src/api/client'

describe('api client environment config', () => {
  it('keeps the API path and timeout as code-level protocol constants', () => {
    expect(API_BASE_PATH).toBe('/api/v1')
    expect(API_TIMEOUT_MS).toBe(10000)
  })

  it('does not wire retired Vite API override variables into the Axios client', () => {
    const clientSource = readFileSync(resolve(__dirname, '../src/api/client.ts'), 'utf-8')

    expect(clientSource).toContain('baseURL: API_BASE_PATH')
    expect(clientSource).toContain('timeout: API_TIMEOUT_MS')
    expect(clientSource).not.toContain('VITE_API_BASE_URL')
    expect(clientSource).not.toContain('VITE_API_TIMEOUT_MS')
  })
})
