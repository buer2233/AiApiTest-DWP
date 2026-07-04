import { readdirSync, readFileSync, statSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const frontendRoot = resolve(__dirname, '..')
const forbiddenEnvironmentUrl = 'https://api.gbif.org'

function collectSourceFiles(path: string): string[] {
  const stat = statSync(path)
  if (stat.isFile()) {
    return [path]
  }

  return readdirSync(path).flatMap((entry) => {
    const childPath = resolve(path, entry)
    const childStat = statSync(childPath)
    if (childStat.isDirectory()) {
      return collectSourceFiles(childPath)
    }
    return [childPath]
  })
}

describe('Stage3 P2 环境地址配置约束', () => {
  it('前端实现层不硬编码模拟环境的真实后端地址', () => {
    // P2 页面应渲染接口返回的 base_url，不能在前端实现层写死阶段种子地址。
    const filesToScan = [
      ...collectSourceFiles(resolve(frontendRoot, 'src')),
      ...collectSourceFiles(resolve(frontendRoot, 'config')),
      resolve(frontendRoot, 'vite.config.ts'),
      resolve(frontendRoot, 'playwright.config.ts'),
    ]

    const offenders = filesToScan.filter((filePath) => readFileSync(filePath, 'utf-8').includes(forbiddenEnvironmentUrl))

    expect(offenders).toEqual([])
  })
})
