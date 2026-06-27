import { computed, unref, type Ref } from "vue";
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";

import { listTestCases, syncTestCases, type ListParams } from "@/api/testcases";

// 用例列表查询：params 变化（筛选/翻页）自动重新请求。
export function useTestCaseList(params: Ref<ListParams>) {
  return useQuery({
    queryKey: computed(() => ["testcases", unref(params)]),
    queryFn: () => listTestCases(unref(params)),
  });
}

// 用例同步：成功后失效列表缓存以刷新。
export function useSyncTestCases() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: syncTestCases,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["testcases"] });
    },
  });
}
