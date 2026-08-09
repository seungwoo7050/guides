import type {
  RecordCommand,
  SyncTransport,
  WireResponse,
} from "@field-notes/sync-engine";

export type FetchLike = (
  input: string,
  init: RequestInit,
) => Promise<Pick<Response, "status" | "text"> & { headers?: Pick<Headers, "get"> }>;

export type SyncCredentialProvider = (signal: AbortSignal) => Promise<string | null>;

const MAX_DECLARED_RESPONSE_BYTES = 1_048_576;
const MAX_RESPONSE_CHARACTERS_AFTER_READ = 1_048_576;

function abortError(message: string): Error {
  const error = new Error(message);
  error.name = "AbortError";
  return error;
}

async function awaitWithAbort<T>(
  pending: Promise<T>,
  signal: AbortSignal,
): Promise<T> {
  if (signal.aborted) throw abortError("sync request aborted");
  let removeListener: () => void = () => undefined;
  const aborted = new Promise<never>((_resolve, reject) => {
    const onAbort = () => reject(abortError("sync request aborted"));
    signal.addEventListener("abort", onAbort, { once: true });
    removeListener = () => signal.removeEventListener("abort", onAbort);
  });
  try {
    return await Promise.race([pending, aborted]);
  } finally {
    removeListener();
  }
}

export function configuredSyncEndpoint(
  configured = process.env.EXPO_PUBLIC_FIELD_NOTES_SYNC_URL,
): string {
  const value = configured?.trim() || "http://127.0.0.1:3104/commands";
  const url = new URL(value);
  if (!(url.protocol === "http:" || url.protocol === "https:")) {
    throw new Error("sync endpoint must use http or https");
  }
  if (url.username !== "" || url.password !== "") {
    throw new Error("sync endpoint must not embed credentials");
  }
  return url.toString();
}

export class FetchSyncTransport implements SyncTransport {
  readonly #endpoint: string;
  readonly #fetch: FetchLike;
  readonly #credential: SyncCredentialProvider;
  readonly #deadlineMs: number;

  public constructor(options: {
    endpoint?: string;
    fetch?: FetchLike;
    credential?: SyncCredentialProvider;
    deadlineMs?: number;
  } = {}) {
    this.#endpoint = configuredSyncEndpoint(options.endpoint);
    this.#fetch = options.fetch ?? globalThis.fetch.bind(globalThis);
    this.#credential = options.credential ?? (async () => null);
    this.#deadlineMs = options.deadlineMs ?? 10_000;
    if (!Number.isFinite(this.#deadlineMs) || this.#deadlineMs <= 0) {
      throw new RangeError("sync request deadline must be positive");
    }
  }

  public async send(
    command: RecordCommand,
    signal: AbortSignal,
  ): Promise<WireResponse> {
    if (signal.aborted) {
      throw abortError("sync transport aborted before send");
    }
    const requestController = new AbortController();
    const abortFromParent = () => requestController.abort(signal.reason);
    signal.addEventListener("abort", abortFromParent, { once: true });
    const deadline = setTimeout(
      () => requestController.abort(new Error("sync request deadline exceeded")),
      this.#deadlineMs,
    );
    try {
      const credential = await awaitWithAbort(
        this.#credential(requestController.signal),
        requestController.signal,
      );
      if (requestController.signal.aborted) {
        throw abortError("sync request aborted after credential lookup");
      }
      const headers: Record<string, string> = {
        accept: "application/json",
        "content-type": "application/json",
      };
      if (credential !== null && credential.trim() !== "") {
        headers.authorization = `Bearer ${credential}`;
      }
      const response = await this.#fetch(this.#endpoint, {
        method: "POST",
        headers,
        body: JSON.stringify(command),
        signal: requestController.signal,
      });
      const declaredLength = Number(response.headers?.get("content-length"));
      if (
        Number.isFinite(declaredLength) &&
        declaredLength > MAX_DECLARED_RESPONSE_BYTES
      ) {
        throw new Error("sync response declares more than 1 MiB");
      }
      const source = await awaitWithAbort(response.text(), requestController.signal);
      // This is a post-read semantic guard, not a streaming memory-allocation cap.
      if (source.length > MAX_RESPONSE_CHARACTERS_AFTER_READ) {
        throw new Error("sync response exceeds the accepted character limit");
      }
      let body: unknown;
      try {
        body = source === "" ? null : JSON.parse(source);
      } catch {
        body = null;
      }
      return { status: response.status, body };
    } finally {
      clearTimeout(deadline);
      signal.removeEventListener("abort", abortFromParent);
    }
  }
}
