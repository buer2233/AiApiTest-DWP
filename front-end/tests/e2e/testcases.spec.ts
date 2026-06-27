import { expect, test, type Page, type Route } from "@playwright/test";

// 用例展示页 E2E：注入登录态 token + mock me/list，验证展示、空态与权限。

function json(route: Route, status: number, body: unknown) {
  return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

const memberMe = { id: 1, username: "m", email: "m@example.test", role: "member", status: "active" };
const adminMe = { id: 2, username: "a", email: "a@example.test", role: "admin", status: "active" };

function mockMe(page: Page, user: unknown) {
  return page.route("**/api/auth/me/", (route) =>
    json(route, 200, { code: 0, message: "ok", data: user }),
  );
}

function emptyList(page: Page) {
  return page.route("**/api/testcases/**", (route) =>
    json(route, 200, { code: 0, message: "ok", data: { count: 0, next: null, previous: null, results: [] } }),
  );
}

test.beforeEach(async ({ page }) => {
  // 注入登录态，路由守卫据此放行受保护页
  await page.addInitScript(() => localStorage.setItem("hermes_token", "tok-e2e"));
});

test("用例列表展示数据", async ({ page }) => {
  await mockMe(page, memberMe);
  await page.route("**/api/testcases/**", (route) =>
    json(route, 200, {
      code: 0,
      message: "ok",
      data: {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 1, module_key: "login", module_name: "login",
            case_path: "test_case/login/test_a.py", node_id: "test_case/login/test_a.py::test_ok",
            function_name: "test_ok", class_name: null, case_title: "正常登录",
            story: "登录", severity: "critical", is_active: true, synced_at: "2026-06-27T00:00:00Z",
          },
          {
            id: 2, module_key: "login", module_name: "login",
            case_path: "test_case/login/test_a.py", node_id: "test_case/login/test_a.py::test_bad",
            function_name: "test_bad", class_name: null, case_title: "错误密码",
            story: "登录", severity: "normal", is_active: true, synced_at: "2026-06-27T00:00:00Z",
          },
        ],
      },
    }),
  );
  await page.goto("/test-cases");
  await expect(page.getByText("正常登录")).toBeVisible();
  await expect(page.getByText("错误密码")).toBeVisible();
});

test("空结果显示空状态提示", async ({ page }) => {
  await mockMe(page, memberMe);
  await emptyList(page);
  await page.goto("/test-cases");
  await expect(page.getByText("暂无用例，请管理员同步")).toBeVisible();
});

test("member 不显示同步用例按钮", async ({ page }) => {
  await mockMe(page, memberMe);
  await emptyList(page);
  await page.goto("/test-cases");
  await expect(page.getByText("成员")).toBeVisible();
  await expect(page.getByRole("button", { name: "同步用例" })).toHaveCount(0);
});

test("admin 显示同步用例按钮", async ({ page }) => {
  await mockMe(page, adminMe);
  await emptyList(page);
  await page.goto("/test-cases");
  await expect(page.getByRole("button", { name: "同步用例" })).toBeVisible();
});
