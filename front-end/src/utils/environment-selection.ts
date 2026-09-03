export interface EnvironmentOption {
  id: number
}

/** 将旧书签中的环境 ID 归一化为当前启用环境。 */
export function resolveEnvironmentId(
  requestedId: string | undefined,
  environments: readonly EnvironmentOption[],
): string {
  if (requestedId && environments.some((environment) => String(environment.id) === requestedId)) {
    return requestedId
  }
  return environments[0] ? String(environments[0].id) : ''
}
