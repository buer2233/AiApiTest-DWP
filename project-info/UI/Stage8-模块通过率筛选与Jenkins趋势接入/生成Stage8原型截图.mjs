import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, join } from 'node:path'
import { createRequire } from 'node:module'

// 该脚本仅用于把本目录 HTML 原型导出为 PNG 评审图。
const currentDir = dirname(fileURLToPath(import.meta.url))
const require = createRequire(import.meta.url)
const { chromium } = require(join(currentDir, '../../../front-end/node_modules/playwright'))

const targets = [
  ['环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-模块通过率页面-方案A.html', '环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-模块通过率页面-方案A.png'],
  ['环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-模块通过率页面-方案B.html', '环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-模块通过率页面-方案B.png'],
  ['环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-用例详情弹窗-方案A.html', '环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-用例详情弹窗-方案A.png'],
  ['环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-用例详情弹窗-方案B.html', '环境与模块通过率页面-模块通过率筛选与Jenkins趋势接入-用例详情弹窗-方案B.png'],
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })

for (const [htmlName, imageName] of targets) {
  await page.goto(pathToFileURL(join(currentDir, htmlName)).href)
  await page.screenshot({ path: join(currentDir, imageName), fullPage: false })
  console.log(`exported ${imageName}`)
}

await browser.close()
