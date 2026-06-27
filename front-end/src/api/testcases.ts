import http from "./http";
import type { ApiSuccess, Paginated, SyncResult, TestCase } from "@/types";

// 用例相关 API（对应后端 /api/testcases/*）。

export interface ListParams {
  page?: number;
  page_size?: number;
  module_key?: string;
  keyword?: string;
}

export async function listTestCases(params: ListParams): Promise<Paginated<TestCase>> {
  const { data } = await http.get<ApiSuccess<Paginated<TestCase>>>("/api/testcases/", {
    params,
  });
  return data.data;
}

export async function syncTestCases(): Promise<SyncResult> {
  const { data } = await http.post<ApiSuccess<SyncResult>>("/api/testcases/sync/");
  return data.data;
}
