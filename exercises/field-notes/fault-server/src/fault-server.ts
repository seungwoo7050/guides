import { ManualClock } from "./control.ts";
import type {
  ConflictBody,
  Fault,
  FaultPlan,
  HistoryEvent,
  IdentityReuseBody,
  MemoizedResponse,
  PermanentFailureBody,
  RecordCommand,
  RecordPayload,
  RemoteRecord,
  ServerSnapshot,
  SuccessBody,
  UnauthorizedBody,
  ValidationFailureBody,
  WireResponse,
} from "./types.ts";

type ParsedCommand =
  | { ok: true; command: RecordCommand }
  | { ok: false; commandId: string | null; reason: string };

type MemoEntry = {
  fingerprint: string;
  response: MemoizedResponse;
};

type HistoryInput = HistoryEvent extends infer Event
  ? Event extends { sequence: number }
    ? Omit<Event, "sequence">
    : never
  : never;

export class ResponseLostError extends Error {
  readonly code = "RESPONSE_LOST";
  readonly commandId: string;

  constructor(commandId: string) {
    super(`response intentionally lost after processing command ${commandId}`);
    this.name = "ResponseLostError";
    this.commandId = commandId;
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isIsoDate(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && Number.isFinite(Date.parse(value));
}

function parsePayload(value: unknown): { ok: true; payload: RecordPayload } | { ok: false; reason: string } {
  if (!isObject(value)) {
    return { ok: false, reason: "payload must be an object" };
  }
  if (typeof value.title !== "string" || typeof value.notes !== "string") {
    return { ok: false, reason: "payload title and notes must be strings" };
  }
  if (value.status !== "draft" && value.status !== "open" && value.status !== "resolved") {
    return { ok: false, reason: "payload status is unsupported" };
  }
  if (!isIsoDate(value.observedAt)) {
    return { ok: false, reason: "payload observedAt must be an ISO-compatible date" };
  }

  let location: RecordPayload["location"];
  if (value.location !== undefined) {
    if (!isObject(value.location)) {
      return { ok: false, reason: "payload location must be an object" };
    }
    const { latitude, longitude, accuracyMeters, measuredAt } = value.location;
    if (
      !isFiniteNumber(latitude) ||
      !isFiniteNumber(longitude) ||
      !isFiniteNumber(accuracyMeters) ||
      accuracyMeters < 0 ||
      !isIsoDate(measuredAt)
    ) {
      return { ok: false, reason: "payload location fields are invalid" };
    }
    location = { latitude, longitude, accuracyMeters, measuredAt };
  }

  const payload: RecordPayload = {
    title: value.title,
    notes: value.notes,
    status: value.status,
    observedAt: value.observedAt,
  };
  if (location !== undefined) {
    payload.location = location;
  }
  return { ok: true, payload };
}

function parseCommand(value: unknown): ParsedCommand {
  if (!isObject(value)) {
    return { ok: false, commandId: null, reason: "command must be an object" };
  }

  const commandId = typeof value.commandId === "string" ? value.commandId : null;
  if (commandId === null || !/^[A-Za-z0-9._:-]{1,128}$/.test(commandId)) {
    return { ok: false, commandId, reason: "commandId is invalid" };
  }
  if (typeof value.recordId !== "string" || !/^[A-Za-z0-9._:-]{1,128}$/.test(value.recordId)) {
    return { ok: false, commandId, reason: "recordId is invalid" };
  }
  if (value.operation !== "upsert" && value.operation !== "delete") {
    return { ok: false, commandId, reason: "operation must be upsert or delete" };
  }
  if (
    value.baseVersion !== null &&
    (!Number.isInteger(value.baseVersion) || (value.baseVersion as number) < 0)
  ) {
    return { ok: false, commandId, reason: "baseVersion must be null or a non-negative integer" };
  }
  if (!Number.isInteger(value.localRevision) || (value.localRevision as number) < 1) {
    return { ok: false, commandId, reason: "localRevision must be a positive integer" };
  }
  if (!isIsoDate(value.createdAt)) {
    return { ok: false, commandId, reason: "createdAt must be an ISO-compatible date" };
  }

  let payload: RecordPayload | null;
  if (value.operation === "delete") {
    if (value.payload !== null) {
      return { ok: false, commandId, reason: "delete command payload must be null" };
    }
    payload = null;
  } else {
    const parsedPayload = parsePayload(value.payload);
    if (!parsedPayload.ok) {
      return { ok: false, commandId, reason: parsedPayload.reason };
    }
    payload = parsedPayload.payload;
  }

  return {
    ok: true,
    command: {
      commandId,
      recordId: value.recordId,
      operation: value.operation,
      baseVersion: value.baseVersion as number | null,
      localRevision: value.localRevision as number,
      payload,
      createdAt: value.createdAt,
    },
  };
}

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (isObject(value)) {
    const result: Record<string, unknown> = {};
    for (const key of Object.keys(value).sort()) {
      result[key] = canonicalize(value[key]);
    }
    return result;
  }
  return value;
}

function fingerprint(command: RecordCommand): string {
  return JSON.stringify(canonicalize(command));
}

function clone<T>(value: T): T {
  return structuredClone(value);
}

function memoizedKind(response: MemoizedResponse): "success" | "conflict" | "permanent-failure" {
  const body = response.body;
  return body.kind;
}

function asReplay(response: MemoizedResponse): MemoizedResponse {
  return {
    status: response.status,
    body: { ...clone(response.body), replayed: true },
  } as MemoizedResponse;
}

function businessValidationReason(command: RecordCommand): string | null {
  if (command.operation === "upsert") {
    if (command.payload === null || command.payload.title.trim().length === 0) {
      return "title-required";
    }
    if (command.payload.title.length > 200) {
      return "title-too-long";
    }
    if (command.payload.notes.length > 10_000) {
      return "notes-too-long";
    }
  }
  return null;
}

export class DeterministicFaultServer {
  readonly clock: ManualClock;
  readonly #records = new Map<string, RemoteRecord>();
  readonly #memo = new Map<string, MemoEntry>();
  readonly #applyCounts = new Map<string, number>();
  readonly #faults: FaultPlan[] = [];
  readonly #history: HistoryEvent[] = [];
  #sequence = 0;

  constructor(clock = new ManualClock()) {
    this.clock = clock;
  }

  inject(fault: Fault, options: { commandId?: string } = {}): void {
    this.#validateFault(fault);
    const plan: FaultPlan = { fault: clone(fault) };
    if (options.commandId !== undefined) {
      plan.commandId = options.commandId;
    }
    this.#faults.push(plan);
  }

  seedRecord(recordId: string, payload: RecordPayload, version = 1): void {
    if (!/^[A-Za-z0-9._:-]{1,128}$/.test(recordId)) {
      throw new TypeError("seed recordId is invalid");
    }
    if (!Number.isInteger(version) || version < 1) {
      throw new RangeError("seed version must be a positive integer");
    }
    const parsed = parsePayload(payload);
    if (!parsed.ok) {
      throw new TypeError(parsed.reason);
    }
    this.#records.set(recordId, {
      recordId,
      payload: clone(parsed.payload),
      version,
      deleted: false,
    });
  }

  async execute(input: unknown): Promise<WireResponse> {
    const parsed = parseCommand(input);
    if (!parsed.ok) {
      const body: ValidationFailureBody = {
        kind: "validation-failure",
        commandId: parsed.commandId,
        reason: parsed.reason,
      };
      return { status: 400, body };
    }

    const command = parsed.command;
    const attemptedFingerprint = fingerprint(command);
    const existing = this.#memo.get(command.commandId);
    if (existing !== undefined && existing.fingerprint !== attemptedFingerprint) {
      this.#record({ kind: "identity-reuse-rejected", commandId: command.commandId });
      const body: IdentityReuseBody = {
        kind: "command-identity-reuse",
        commandId: command.commandId,
        reason: "same-command-id-different-attempted-command",
      };
      return { status: 409, body };
    }

    const fault = this.#takeFault(command.commandId);
    if (fault !== undefined) {
      this.#record({ kind: "fault-consumed", commandId: command.commandId, fault: fault.kind });
      if (fault.kind === "delay") {
        const until = this.clock.now() + fault.milliseconds;
        this.#record({ kind: "delayed", commandId: command.commandId, until });
        await this.clock.sleep(fault.milliseconds);
      }
      if (fault.kind === "unauthorized") {
        this.#record({ kind: "unauthorized", commandId: command.commandId });
        const body: UnauthorizedBody = { kind: "unauthorized", commandId: command.commandId };
        return { status: 401, body };
      }
    }

    const memoAfterDelay = this.#memo.get(command.commandId);
    let response: MemoizedResponse;
    if (memoAfterDelay !== undefined) {
      this.#record({ kind: "replayed", commandId: command.commandId });
      response = asReplay(memoAfterDelay.response);
    } else if (fault?.kind === "permanent-validation") {
      const body: PermanentFailureBody = {
        kind: "permanent-failure",
        commandId: command.commandId,
        reason: fault.reason,
        replayed: false,
      };
      response = { status: 422, body };
      this.#memoize(command, attemptedFingerprint, response);
    } else {
      const validationReason = businessValidationReason(command);
      if (validationReason !== null) {
        const body: PermanentFailureBody = {
          kind: "permanent-failure",
          commandId: command.commandId,
          reason: validationReason,
          replayed: false,
        };
        response = { status: 422, body };
        this.#memoize(command, attemptedFingerprint, response);
      } else {
        response = this.#applyOrConflict(command);
        this.#memoize(command, attemptedFingerprint, response);
      }
    }

    return this.#deliver(command.commandId, response, fault);
  }

  getRecord(recordId: string): RemoteRecord | null {
    const record = this.#records.get(recordId);
    return record === undefined ? null : clone(record);
  }

  getApplyCount(commandId: string): number {
    return this.#applyCounts.get(commandId) ?? 0;
  }

  snapshot(): ServerSnapshot {
    return {
      now: this.clock.now(),
      records: [...this.#records.values()]
        .map((record) => clone(record))
        .sort((left, right) => left.recordId.localeCompare(right.recordId)),
      memoizedCommandIds: [...this.#memo.keys()].sort(),
      applyCountByCommand: Object.fromEntries(
        [...this.#applyCounts.entries()].sort(([left], [right]) => left.localeCompare(right)),
      ),
      pendingFaults: clone(this.#faults),
      history: clone(this.#history),
    };
  }

  reset(): void {
    this.#records.clear();
    this.#memo.clear();
    this.#applyCounts.clear();
    this.#faults.splice(0);
    this.#history.splice(0);
    this.#sequence = 0;
    this.clock.reset(0);
  }

  #applyOrConflict(command: RecordCommand): MemoizedResponse {
    const current = this.#records.get(command.recordId) ?? null;
    const currentVersion = current?.version ?? null;

    if (command.baseVersion !== currentVersion) {
      const body: ConflictBody = {
        kind: "conflict",
        commandId: command.commandId,
        recordId: command.recordId,
        expectedBaseVersion: command.baseVersion,
        current: current === null ? null : clone(current),
        replayed: false,
      };
      return { status: 409, body };
    }

    const version = (currentVersion ?? 0) + 1;
    const record: RemoteRecord = {
      recordId: command.recordId,
      payload: command.operation === "delete" ? null : clone(command.payload),
      version,
      deleted: command.operation === "delete",
    };
    this.#records.set(command.recordId, record);
    this.#applyCounts.set(command.commandId, this.getApplyCount(command.commandId) + 1);
    this.#record({
      kind: "applied",
      commandId: command.commandId,
      recordId: command.recordId,
      version,
    });

    const body: SuccessBody = {
      kind: "success",
      commandId: command.commandId,
      record: clone(record),
      replayed: false,
    };
    return { status: 200, body };
  }

  #memoize(command: RecordCommand, attemptedFingerprint: string, response: MemoizedResponse): void {
    this.#memo.set(command.commandId, {
      fingerprint: attemptedFingerprint,
      response: clone(response),
    });
    this.#record({
      kind: "memoized",
      commandId: command.commandId,
      result: memoizedKind(response),
    });
  }

  #deliver(commandId: string, response: MemoizedResponse, fault: Fault | undefined): WireResponse {
    if (fault?.kind === "response-loss") {
      this.#record({ kind: "response-lost", commandId });
      throw new ResponseLostError(commandId);
    }

    if (fault?.kind === "malformed-success" && response.status === 200) {
      this.#record({ kind: "malformed-sent", commandId });
      return {
        status: 200,
        body: Object.hasOwn(fault, "body")
          ? clone(fault.body)
          : { kind: "success", commandId, record: "malformed-record" },
      };
    }

    if (fault?.kind === "version-regression" && response.status === 200) {
      const by = fault.by ?? 1;
      const body = clone(response.body);
      body.record.version = Math.max(0, body.record.version - by);
      this.#record({
        kind: "version-regression-sent",
        commandId,
        version: body.record.version,
      });
      return { status: 200, body };
    }

    return clone(response);
  }

  #takeFault(commandId: string): Fault | undefined {
    const index = this.#faults.findIndex(
      (plan) => plan.commandId === undefined || plan.commandId === commandId,
    );
    if (index < 0) {
      return undefined;
    }
    const [plan] = this.#faults.splice(index, 1);
    return plan?.fault;
  }

  #validateFault(fault: Fault): void {
    if (fault.kind === "delay" && (!Number.isFinite(fault.milliseconds) || fault.milliseconds < 0)) {
      throw new RangeError("delay fault requires non-negative finite milliseconds");
    }
    if (
      fault.kind === "version-regression" &&
      fault.by !== undefined &&
      (!Number.isInteger(fault.by) || fault.by < 1)
    ) {
      throw new RangeError("version-regression by must be a positive integer");
    }
    if (fault.kind === "permanent-validation" && fault.reason.trim().length === 0) {
      throw new TypeError("permanent-validation reason is required");
    }
  }

  #record(event: HistoryInput): void {
    this.#history.push({ ...event, sequence: this.#sequence++ } as HistoryEvent);
  }
}
