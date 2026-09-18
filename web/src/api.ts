export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...options,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const data = await response
    .json()
    .catch(() => ({ error: "서버 응답을 읽을 수 없습니다." }));
  if (!response.ok)
    throw new ApiError(
      data.error || "요청을 처리하지 못했습니다.",
      response.status,
    );
  return data as T;
}
export const formatNumber = (value: number) => value.toLocaleString("ko-KR");
export const formatDate = (value: string) =>
  new Date(value).toLocaleDateString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
  });
export const errorMessage = (error: unknown) =>
  error instanceof TypeError
    ? "서버에 연결할 수 없습니다. 연결을 확인하고 다시 시도해 주세요."
    : error instanceof Error
      ? error.message
      : "다시 시도해 주세요.";
