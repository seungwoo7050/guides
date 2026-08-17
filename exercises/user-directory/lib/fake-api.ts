// [Implementation 2] Keep delay, failure, and AbortSignal ownership in an asynchronous adapter outside the UI.
export interface User { id: string; handle: string; displayName: string }

const users: User[] = [
  { id: "u1", handle: "alpha", displayName: "Alpha" },
  { id: "u2", handle: "beta", displayName: "Beta" },
  { id: "u3", handle: "gamma", displayName: "Gamma" }
];

export async function searchUsers(query: string, signal: AbortSignal): Promise<User[]> {
  signal.throwIfAborted();
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, query === "a" ? 500 : 150);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException("aborted", "AbortError"));
    };
    signal.addEventListener("abort", onAbort, { once: true });
  });
  if (query === "error") throw new Error("Intentional search failure");
  const normalized = query.trim().toLowerCase();
  return normalized
    ? users.filter((user) => `${user.handle} ${user.displayName}`.toLowerCase().includes(normalized))
    : users;
}
