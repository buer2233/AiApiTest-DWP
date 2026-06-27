import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

// mock 认证 API，避免真实请求
vi.mock("@/api/auth", () => ({
  login: vi.fn(),
  logout: vi.fn(),
  fetchMe: vi.fn(),
  register: vi.fn(),
}));

import * as authApi from "@/api/auth";
import { useAuthStore } from "@/stores/auth";

const activeMember = {
  id: 1,
  username: "member1",
  email: "member1@example.test",
  role: "member" as const,
  status: "active" as const,
};

const adminUser = { ...activeMember, id: 2, username: "admin1", role: "admin" as const };

describe("auth store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("login 设置 token 与 user，并持久化到 localStorage", async () => {
    vi.mocked(authApi.login).mockResolvedValue({ token: "tok-123", user: activeMember });
    const store = useAuthStore();
    await store.login("member1", "pw");
    expect(store.token).toBe("tok-123");
    expect(store.isAuthenticated).toBe(true);
    expect(store.user?.username).toBe("member1");
    expect(localStorage.getItem("hermes_token")).toBe("tok-123");
  });

  it("isAdmin 仅在 admin 角色时为 true", async () => {
    vi.mocked(authApi.login).mockResolvedValue({ token: "t", user: adminUser });
    const store = useAuthStore();
    await store.login("admin1", "pw");
    expect(store.isAdmin).toBe(true);
  });

  it("member 角色 isAdmin 为 false", async () => {
    vi.mocked(authApi.login).mockResolvedValue({ token: "t", user: activeMember });
    const store = useAuthStore();
    await store.login("member1", "pw");
    expect(store.isAdmin).toBe(false);
  });

  it("logout 清除 token 与 user", async () => {
    vi.mocked(authApi.login).mockResolvedValue({ token: "t", user: activeMember });
    vi.mocked(authApi.logout).mockResolvedValue();
    const store = useAuthStore();
    await store.login("member1", "pw");
    await store.logout();
    expect(store.token).toBeNull();
    expect(store.user).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(localStorage.getItem("hermes_token")).toBeNull();
  });

  it("logout 即使后端报错也清除本地登录态", async () => {
    vi.mocked(authApi.login).mockResolvedValue({ token: "t", user: activeMember });
    vi.mocked(authApi.logout).mockRejectedValue(new Error("network"));
    const store = useAuthStore();
    await store.login("member1", "pw");
    await store.logout();
    expect(store.token).toBeNull();
    expect(localStorage.getItem("hermes_token")).toBeNull();
  });
});
