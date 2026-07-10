import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { fetchModuleSnapshotTrend } from '@/api/metrics'
import ModuleTrendDialog from '@/components/metrics/ModuleTrendDialog.vue'
import type { ModuleSnapshot, ModuleTrend } from '@/types/metrics'

vi.mock('@/api/metrics', () => ({
  fetchModuleSnapshotTrend: vi.fn(),
}))

const mockedFetchTrend = vi.mocked(fetchModuleSnapshotTrend)

const DialogStub = defineComponent({
  props: {
    modelValue: Boolean,
    title: String,
  },
  template: '<section role="dialog" :aria-label="title"><slot /><slot name="footer" /></section>',
})

const snapshot = {
  id: 2,
  completed_at: '2026-07-10T10:00:00+08:00',
  package_name: 'test_gbif_case_module2',
  module_name: '物种数据2',
  module_dev: '张三',
  module_test: '李四',
  total_count: 10,
  failed_count: 1,
  skipped_count: 1,
  pass_rate: '0.900000',
  duration_seconds: '5.09',
  actions: {
    failed_rerun: true,
    module_rerun: true,
    trend_7d: true,
    trend_30d: true,
    jenkins_tasks: true,
  },
} satisfies ModuleSnapshot

function mountBaseDialog(days: 7 | 30 = 7) {
  return mount(ModuleTrendDialog, {
    props: {
      modelValue: true,
      snapshot,
      environmentName: '模拟测试环境',
      days,
    },
    global: {
      stubs: {
        'el-dialog': DialogStub,
      },
      directives: {
        loading: () => undefined,
      },
    },
  })
}

function mountDialog(trend: ModuleTrend, days: 7 | 30 = 7) {
  mockedFetchTrend.mockResolvedValueOnce(trend)
  return mountBaseDialog(days)
}

describe('Stage11 模块趋势真实折线图', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('按固定 0%-100% 坐标绘制全部真实点位和可访问数值', async () => {
    const wrapper = mountDialog({
      module: {
        snapshot_id: 2,
        module_name: '物种数据2',
        package_name: 'test_gbif_case_module2',
        environment_name: '模拟测试环境',
      },
      days: 7,
      series: [
        { run_date: '2026-07-08', run_type: 'daily_full', total_count: 10, failed_count: 0, skipped_count: 1, pass_rate: '1.000000', duration_seconds: '5.00' },
        { run_date: '2026-07-09', run_type: 'module_rerun', total_count: 10, failed_count: 5, skipped_count: 1, pass_rate: '0.500000', duration_seconds: '6.00' },
        { run_date: '2026-07-10', run_type: 'module_rerun', total_count: 10, failed_count: 1, skipped_count: 1, pass_rate: '0.900000', duration_seconds: '5.09' },
      ],
    })
    await flushPromises()

    const chart = wrapper.get('svg[aria-label="通过率趋势折线图"]')
    const circles = chart.findAll('circle')
    expect(circles).toHaveLength(3)
    expect(chart.attributes('role')).toBe('group')
    expect(chart.get('polyline').attributes('points')).not.toContain('NaN')
    expect(circles.map((circle) => circle.attributes('cy'))).toEqual(['24', '80', '35.2'])
    expect(circles[2].attributes('aria-label')).toContain('2026-07-10 module_rerun 90.00%')
    expect(circles[2].attributes('tabindex')).toBe('0')
    expect(circles[2].attributes('role')).toBe('img')
    expect(circles[2].get('title').text()).toContain('2026-07-10 module_rerun 90.00%')
    expect(chart.findAll('.trend-dialog__axis-label--y').map((label) => label.text())).toEqual(['100%', '50%', '0%'])
    expect(chart.findAll('.trend-dialog__axis-label--x')).toHaveLength(3)
  })

  it('30天数据绘制全部点位但限制横轴日期标签数量', async () => {
    const series = Array.from({ length: 30 }, (_, index) => ({
      run_date: `2026-06-${String(index + 1).padStart(2, '0')}`,
      run_type: index === 29 ? 'module_rerun' : 'daily_full',
      total_count: 10,
      failed_count: index % 4,
      skipped_count: 1,
      pass_rate: ((10 - (index % 4)) / 10).toFixed(6),
      duration_seconds: '5.00',
    }))
    const wrapper = mountDialog(
      {
        module: {
          snapshot_id: 2,
          module_name: '物种数据2',
          package_name: 'test_gbif_case_module2',
          environment_name: '模拟测试环境',
        },
        days: 30,
        series,
      },
      30,
    )
    await flushPromises()

    const chart = wrapper.get('svg[aria-label="通过率趋势折线图"]')
    expect(chart.findAll('circle')).toHaveLength(30)
    expect(chart.findAll('.trend-dialog__axis-label--x').length).toBeLessThanOrEqual(7)
    expect(chart.findAll('.trend-dialog__axis-label--x').length).toBeGreaterThanOrEqual(2)
  })

  it('单点使用真实百分比高度，空数据不渲染折线', async () => {
    const single = mountDialog({
      module: {
        snapshot_id: 2,
        module_name: '物种数据2',
        package_name: 'test_gbif_case_module2',
        environment_name: '模拟测试环境',
      },
      days: 7,
      series: [
        { run_date: '2026-07-10', run_type: 'module_rerun', total_count: 10, failed_count: 2, skipped_count: 1, pass_rate: '0.800000', duration_seconds: '5.00' },
      ],
    })
    await flushPromises()
    expect(single.get('circle').attributes('cy')).toBe('46.4')
    expect(single.get('polyline').attributes('points')).toBe('48,46.4')

    single.unmount()
    const empty = mountDialog({
      module: {
        snapshot_id: 2,
        module_name: '物种数据2',
        package_name: 'test_gbif_case_module2',
        environment_name: '模拟测试环境',
      },
      days: 7,
      series: [],
    })
    await flushPromises()
    expect(empty.find('polyline').exists()).toBe(false)
    expect(empty.text()).toContain('暂无趋势数据')
  })

  it('请求失败时只展示错误提示，不叠加空数据状态', async () => {
    mockedFetchTrend.mockRejectedValueOnce(new Error('network failure'))
    const wrapper = mountBaseDialog()
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toBe('请求失败，请稍后重试。')
    expect(wrapper.text()).not.toContain('暂无趋势数据')
    expect(wrapper.text()).not.toContain('无历史记录')
  })
})
