import {
  BoundedSyncWorker,
  FixedSyncBudget,
  type RecordCommand,
} from "@field-notes/sync-engine";
import { SQLiteFieldNotesRepository } from "../src/storage/SQLiteFieldNotesRepository";
import { sequentialIds } from "../src/storage/testing/DeterministicLocalStore";
import {
  configuredSyncEndpoint,
  FetchSyncTransport,
  type FetchLike,
} from "../src/sync/FetchSyncTransport";
import { SQLiteSyncRepositoryAdapter } from "../src/sync/SQLiteSyncRepositoryAdapter";
import { NodeSQLiteDatabase } from "./support/NodeSQLiteDatabase";

const COMMAND: RecordCommand = {
  commandId: "fetch-command",
  recordId: "fetch-record",
  operation: "upsert",
  baseVersion: null,
  localRevision: 1,
  payload: {
    title: "fetch payload",
    notes: "local test only",
    status: "open",
    observedAt: "2026-08-09T17:00:00.000Z",
  },
  createdAt: "2026-08-09T17:00:01.000Z",
};

describe("Stage 04 production fetch transport", () => {
  it("posts the stable command to a configurable endpoint without embedded credentials", async () => {
    const calls: Array<{ url: string; init: RequestInit }> = [];
    const fetch: FetchLike = async (url, init) => {
      calls.push({ url, init });
      return {
        status: 200,
        headers: new Headers({ "content-length": "120" }),
        text: async () => JSON.stringify({
          kind: "success",
          commandId: COMMAND.commandId,
          record: {
            recordId: COMMAND.recordId,
            payload: COMMAND.payload,
            version: 1,
            deleted: false,
          },
        }),
      };
    };
    const transport = new FetchSyncTransport({
      endpoint: "http://127.0.0.1:4317/commands",
      fetch,
      credential: async () => "test-session",
      deadlineMs: 100,
    });
    const result = await transport.send(COMMAND, new AbortController().signal);
    expect(result.status).toBe(200);
    expect(calls).toHaveLength(1);
    expect(calls[0]?.url).toBe("http://127.0.0.1:4317/commands");
    expect(JSON.parse(String(calls[0]?.init.body))).toEqual(COMMAND);
    expect(calls[0]?.init.headers).toMatchObject({
      authorization: "Bearer test-session",
      "content-type": "application/json",
    });
    expect(() => configuredSyncEndpoint("file:///private/backend"))
      .toThrow("http or https");
    expect(() => configuredSyncEndpoint("https://user:secret@example.test/commands"))
      .toThrow("must not embed credentials");
    expect(() => configuredSyncEndpoint("https://example.com/commands"))
      .toThrow("loopback or a reserved HTTPS .test host");
    expect(() => configuredSyncEndpoint("http://example.test/commands"))
      .toThrow("loopback or a reserved HTTPS .test host");
    expect(configuredSyncEndpoint("https://example.test/commands"))
      .toBe("https://example.test/commands");
  });

  it("preserves caller abort and clears its composed request", async () => {
    let requestSignal: AbortSignal | undefined;
    const fetch: FetchLike = (_url, init) => {
      requestSignal = init.signal ?? undefined;
      return new Promise((_resolve, reject) => {
        requestSignal?.addEventListener("abort", () => {
          const error = new Error("aborted by test");
          error.name = "AbortError";
          reject(error);
        });
      });
    };
    const transport = new FetchSyncTransport({ fetch, deadlineMs: 10_000 });
    const parent = new AbortController();
    const pending = transport.send(COMMAND, parent.signal);
    while (requestSignal === undefined) await Promise.resolve();
    parent.abort(new Error("parent stopped"));
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    expect(requestSignal?.aborted).toBe(true);
  });

  it("aborts while credential lookup is pending and never reaches fetch", async () => {
    let credentialSignal: AbortSignal | undefined;
    const fetch = jest.fn<ReturnType<FetchLike>, Parameters<FetchLike>>();
    const transport = new FetchSyncTransport({
      fetch,
      credential: (signal) => {
        credentialSignal = signal;
        return new Promise(() => undefined);
      },
      deadlineMs: 10_000,
    });
    const parent = new AbortController();
    const pending = transport.send(COMMAND, parent.signal);
    while (credentialSignal === undefined) await Promise.resolve();
    parent.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    expect(credentialSignal.aborted).toBe(true);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("does not call fetch when parent abort wins the credential-resolution race", async () => {
    let resolveCredential: ((value: string | null) => void) | undefined;
    const credential = new Promise<string | null>((resolve) => {
      resolveCredential = resolve;
    });
    const fetch = jest.fn<ReturnType<FetchLike>, Parameters<FetchLike>>();
    const transport = new FetchSyncTransport({
      fetch,
      credential: async () => credential,
      deadlineMs: 10_000,
    });
    const parent = new AbortController();
    const pending = transport.send(COMMAND, parent.signal);
    while (resolveCredential === undefined) await Promise.resolve();
    resolveCredential("credential");
    parent.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("turns a deterministic never-response deadline into durable UNKNOWN retry_wait", async () => {
    jest.useFakeTimers();
    const database = new NodeSQLiteDatabase();
    const repository = new SQLiteFieldNotesRepository({
      ids: sequentialIds(),
      clock: { now: () => "2026-08-09T17:00:00.000Z" },
      openDatabase: async () => database.asExpoDatabase(),
    });
    await repository.ready();
    const record = await repository.get("forest-edge");
    if (record === null) throw new Error("fixture missing");
    const saved = await repository.saveWithCommand({
      id: record.id,
      expectedLocalRevision: record.localRevision,
      payload: {
        title: "timeout must not block edit",
        notes: record.notes,
        status: record.status,
        observedAt: record.observedAt,
      },
    });
    let requestSignal: AbortSignal | undefined;
    const neverResponds: FetchLike = (_url, init) => {
      requestSignal = init.signal ?? undefined;
      return new Promise((_resolve, reject) => {
        requestSignal?.addEventListener("abort", () => {
          const error = new Error("deadline abort");
          error.name = "AbortError";
          reject(error);
        });
      });
    };
    const sync = new SQLiteSyncRepositoryAdapter(repository, {
      nextLeaseToken: () => "timeout-lease",
      now: () => 0,
    });
    const worker = new BoundedSyncWorker({
      repository: sync,
      transport: new FetchSyncTransport({
        fetch: neverResponds,
        deadlineMs: 25,
      }),
      clock: { now: () => 0 },
      budget: new FixedSyncBudget({
        maxCommands: 1,
        leaseDurationMs: 100,
        retryDelayMs: 10,
      }),
    });
    const run = worker.run({ trigger: "manual", workerId: "timeout-worker" });
    while (requestSignal === undefined) await Promise.resolve();
    await jest.advanceTimersByTimeAsync(25);
    const result = await run;
    expect(result.checkpoints[0]?.state).toBe("retry_wait");
    const waiting = await sync.getCommand(saved.command.commandId);
    expect(waiting?.state).toMatchObject({
      kind: "retry_wait",
      attempted: expect.objectContaining({
        commandId: saved.command.commandId,
        recordId: saved.command.recordId,
        payload: expect.objectContaining({ title: "timeout must not block edit" }),
      }),
      reason: expect.stringContaining("AbortError"),
    });
    expect(await repository.get(record.id)).toMatchObject({
      title: "timeout must not block edit",
      remoteVersion: null,
      syncState: "retry-wait",
    });
    database.close();
    jest.useRealTimers();
  });

  it("settles its deadline even when an injected fetch ignores AbortSignal", async () => {
    jest.useFakeTimers();
    const ignoresAbort: FetchLike = async () => new Promise(() => undefined);
    const transport = new FetchSyncTransport({
      fetch: ignoresAbort,
      deadlineMs: 25,
    });
    const pending = transport.send(COMMAND, new AbortController().signal);
    const rejected = expect(pending).rejects.toMatchObject({ name: "AbortError" });
    await jest.advanceTimersByTimeAsync(25);
    await rejected;
    jest.useRealTimers();
  });

  it("rejects declared oversize responses before reading and treats invalid JSON as data", async () => {
    const read = jest.fn(async () => "ignored");
    const oversized = new FetchSyncTransport({
      fetch: async () => ({
        status: 200,
        headers: new Headers({ "content-length": "1048577" }),
        text: read,
      }),
    });
    await expect(oversized.send(COMMAND, new AbortController().signal))
      .rejects.toThrow("declares more than 1 MiB");
    expect(read).not.toHaveBeenCalled();

    const malformed = new FetchSyncTransport({
      fetch: async () => ({ status: 200, text: async () => "not-json" }),
    });
    await expect(malformed.send(COMMAND, new AbortController().signal))
      .resolves.toEqual({ status: 200, body: null });
  });
});
