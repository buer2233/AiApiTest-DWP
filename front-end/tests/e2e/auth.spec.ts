import { expect, test, type Route } from "@playwright/test";

// 用 page.route mock 后端 API，隔离验证登录/注册前端行为，不依赖真实 Django。

function json(route: Route, status: number, body: unknown) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

test.describe("登录与注册", () => {
  test("active 用户登录成功跳转用例页", async ({ page }) => {
    await page.route("**/api/auth/login/", (route) =>
      json(route, 200, {
        code: 0,
        message: "登录成功",
        data: {
          token: "tok-1",
          user: { id: 1, username: "u", email: "u@example.test", role: "member", status: "active" },
        },
      }),
    );
    await page.route("**/api/auth/me/", (route) =>
      json(route, 200, {
        code: 0,
        message: "ok",
        data: { id: 1, username: "u", email: "u@example.test", role: "member", status: "active" },
      }),
    );
    await page.route("**/api/testcases/**", (route) =>
      json(route, 200, { code: 0, message: "ok", data: { count: 0, next: null, previous: null, results: [] } }),
    );

    await page.goto("/login");
    await page.getByPlaceholder("请输入用户名").fill("u");
    await page.getByPlaceholder("请输入密码").fill("pw");
    await page.getByRole("button", { name: "登录" }).click();
    await expect(page).toHaveURL(/\/test-cases/);
  });

  test("pending 用户登录显示待审批文案", async ({ page }) => {
    await page.route("**/api/auth/login/", (route) =>
      json(route, 403, { code: 1102, message: "账号待管理员审批", errors: {} }),
    );
    await page.goto("/login");
    await page.getByPlaceholder("请输入用户名").fill("p");
    await page.getByPlaceholder("请输入密码").fill("pw");
    await page.getByRole("button", { name: "登录" }).click();
    await expect(page.getByText("账号待管理员审批")).toBeVisible();
  });

  test("密码错误显示统一防枚举提示", async ({ page }) => {
    await page.route("**/api/auth/login/", (route) =>
      json(route, 400, { code: 1101, message: "用户名或密码错误", errors: {} }),
    );
    await page.goto("/login");
    await page.getByPlaceholder("请输入用户名").fill("u");
    await page.getByPlaceholder("请输入密码").fill("wrong");
    await page.getByRole("button", { name: "登录" }).click();
    await expect(page.getByText("用户名或密码错误")).toBeVisible();
  });

  test("注册成功提示待审批并回登录页", async ({ page }) => {
    await page.route("**/api/auth/register/", (route) =>
      json(route, 201, {
        code: 0,
        message: "注册成功，待管理员审批",
        data: { id: 5, username: "new", email: "new@example.test", status: "pending", role: "member" },
      }),
    );
    await page.goto("/register");
    await page.getByPlaceholder("3-150 个字符").fill("newuser");
    await page.getByPlaceholder("请输入邮箱").fill("new@example.test");
    await page.getByPlaceholder("至少 8 位").fill("Hermes#Test2026");
    await page.getByPlaceholder("再次输入密码").fill("Hermes#Test2026");
    await page.getByRole("button", { name: "注册" }).click();
    await expect(page).toHaveURL(/\/login/);
  });

  test("注册用户名重复显示字段错误", async ({ page }) => {
    await page.route("**/api/auth/register/", (route) =>
      json(route, 400, { code: 1001, message: "用户名已被占用", errors: {} }),
    );
    await page.goto("/register");
    await page.getByPlaceholder("3-150 个字符").fill("existing");
    await page.getByPlaceholder("请输入邮箱").fill("e@example.test");
    await page.getByPlaceholder("至少 8 位").fill("Hermes#Test2026");
    await page.getByPlaceholder("再次输入密码").fill("Hermes#Test2026");
    await page.getByRole("button", { name: "注册" }).click();
    await expect(page.getByText("用户名已被占用")).toBeVisible();
  });

  test("未登录访问用例页重定向登录", async ({ page }) => {
    await page.goto("/test-cases");
    await expect(page).toHaveURL(/\/login/);
  });
});
