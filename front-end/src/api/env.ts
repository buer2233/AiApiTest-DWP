export function resolveApiTimeoutMs(value: string | undefined, fallback = 10000): number {
  const parsed = Number(value)
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return fallback
  }
  return parsed
}
