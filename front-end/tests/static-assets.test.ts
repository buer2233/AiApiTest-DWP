import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const frontendRoot = resolve(__dirname, '..')

describe('static browser assets', () => {
  it('declares an existing favicon to avoid browser favicon 404 noise', () => {
    const indexHtml = readFileSync(resolve(frontendRoot, 'index.html'), 'utf-8')
    const hrefMatch = indexHtml.match(/<link\s+rel="icon"\s+type="image\/svg\+xml"\s+href="([^"]+)"\s*\/>/)

    expect(hrefMatch?.[1]).toBe('/favicon.svg')
    expect(existsSync(resolve(frontendRoot, 'public/favicon.svg'))).toBe(true)
  })
})
