import { test, type Route } from "@playwright/test";

// 关键页面截图证据生成（非断言测试）。运行：npx playwright test capture.spec.ts
// 截图输出到 tests/screenshots/（git 忽略，作为阶段验收证据本地留存）。

function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

test("截图-登录页", async ({ page }) => {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "tests/screenshots/01-login.png", fullPage: true });
});

test("截图-注册页", async ({ page }) => {
  await page.goto("/register");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "tests/screenshots/02-register.png", fullPage: true });
});

test("截图-用例展示页（admin + 数据）", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("hermes_token", "tok"));
  await page.route("**/api/auth/me/", (r) =>
    json(r, {
      code: 0,
      message: "ok",
      data: { id: 2, username: "admin", email: "a@example.test", role: "admin", status: "active" },
    }),
  );
  await page.route("**/api/testcases/**", (r) =>
    json(r, {
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
            function_name: "test_ok", class_name: null, case_title: "正常登录返回 token",
            story: "登录", severity: "critical", is_active: true, synced_at: "2026-06-27T00:00:00Z",
          },
          {
            id: 2, module_key: "testcase", module_name: "testcase",
            case_path: "test_case/tc/test_sync.py", node_id: "test_case/tc/test_sync.py::test_sync",
            function_name: "test_sync", class_name: null, case_title: "同步解析入库",
            story: "同步", severity: "blocker", is_active: true, synced_at: "2026-06-27T00:00:00Z",
          },
        ],
      },
    }),
  );
  await page.goto("/test-cases");
  await page.getByText("正常登录返回 token").waitFor();
  await page.screenshot({ path: "tests/screenshots/03-testcases.png", fullPage: true });
});
