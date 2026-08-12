// [Implementation 2] UI 밖의 비동기 adapter가 지연·실패와 AbortSignal 수명을 소유하도록 분리합니다.
export interface User { id: string; handle: string; displayName: string }
const users: User[] = [
  { id: "u1", handle: "alpha", displayName: "알파" },
  { id: "u2", handle: "beta", displayName: "베타" },
  { id: "u3", handle: "gamma", displayName: "감마" }
];

export async function searchUsers(query: string, signal: AbortSignal): Promise<User[]> {
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, query === "a" ? 500 : 150);
    signal.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(new DOMException("aborted", "AbortError"));
    }, { once: true });
  });
  if (query === "error") throw new Error("의도적 검색 실패");
  const normalized = query.trim().toLowerCase();
  return normalized ? users.filter((user) => `${user.handle} ${user.displayName}`.toLowerCase().includes(normalized)) : users;
}
