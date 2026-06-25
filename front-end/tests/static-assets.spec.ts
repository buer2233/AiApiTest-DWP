/**
 * 前端静态资源测试。
 * 覆盖浏览器会自动请求的站点图标，防止开发环境控制台出现 favicon 404。
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

describe('static assets', () => {
  it('provides a favicon referenced by the HTML entry', () => {
    /** Vite public 目录中的 favicon.svg 会按根路径提供给浏览器。 */
    const faviconPath = resolve(__dirname, '../public/favicon.svg');
    expect(existsSync(faviconPath)).toBe(true);

    const htmlEntry = readFileSync(resolve(__dirname, '../index.html'), 'utf-8');
    expect(htmlEntry).toContain('rel="icon"');
    expect(htmlEntry).toContain('href="/favicon.svg"');
  });
});
