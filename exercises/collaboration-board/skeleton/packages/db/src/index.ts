export interface ApplicationRepository {
  close(): Promise<void>;
}

export function createMemoryRepository(): ApplicationRepository {
  let closed = false;
  return {
    async close() {
      if (closed) return;
      closed = true;
    }
  };
}
