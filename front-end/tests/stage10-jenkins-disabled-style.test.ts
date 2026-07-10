import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const mainCss = readFileSync(resolve(process.cwd(), 'src/assets/main.css'), 'utf-8')
const dialogSource = readFileSync(resolve(process.cwd(), 'src/components/metrics/JenkinsTasksDialog.vue'), 'utf-8')

describe('Stage10 Jenkins 任务禁用按钮视觉契约', () => {
  it('全局主题提供明确的灰色禁用 token', () => {
    expect(mainCss).toContain('--color-disabled-bg:')
    expect(mainCss).toContain('--color-disabled-border:')
    expect(mainCss).toContain('--color-disabled-text:')
  })

  it('取消按钮禁用和 hover 状态保持灰色且不可点击', () => {
    expect(dialogSource).toMatch(/\.secondary-button:disabled[\s\S]*\.secondary-button:disabled:hover/)
    expect(dialogSource).toContain('background: var(--color-disabled-bg)')
    expect(dialogSource).toContain('border-color: var(--color-disabled-border)')
    expect(dialogSource).toContain('color: var(--color-disabled-text)')
    expect(dialogSource).toContain('cursor: not-allowed')
    expect(dialogSource).toContain(':disabled="!task.actions.cancel || cancelingTaskId !== null"')
  })
})
