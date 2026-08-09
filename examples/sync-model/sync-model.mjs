function clone(value) {
  return structuredClone(value);
}

function validatePayload(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("payload must be an object");
  }
  if (typeof payload.title !== "string" || payload.title.trim() === "") {
    throw new Error("payload.title is required");
  }
  if (typeof payload.notes !== "string") {
    throw new Error("payload.notes is required");
  }
  if (!new Set(["open", "closed"]).has(payload.status)) {
    throw new Error("payload.status is invalid");
  }
}

function command({ commandId, localRevision, baseVersion, payload }) {
  if (typeof commandId !== "string" || commandId === "") {
    throw new Error("commandId is required");
  }
  if (!Number.isInteger(localRevision) || localRevision < 0) {
    throw new Error("localRevision must be a non-negative integer");
  }
  if (baseVersion !== null && (!Number.isInteger(baseVersion) || baseVersion < 0)) {
    throw new Error("baseVersion must be null or a non-negative integer");
  }
  validatePayload(payload);
  return {
    commandId,
    localRevision,
    baseVersion,
    payload: clone(payload),
  };
}

function emptyControlState() {
  return {
    active: null,
    retry: null,
    queued: null,
    blocked: null,
    terminal: null,
    conflict: null,
    lastError: null,
  };
}

export function createLocalRecord({ id, payload, commandId }) {
  const state = {
    id,
    local: { revision: 1, payload: clone(payload) },
    remote: null,
    ...emptyControlState(),
    queued: command({ commandId, localRevision: 1, baseVersion: null, payload }),
  };
  assertValid(state);
  return state;
}

export function createSyncedRecord({ id, payload, version }) {
  validateServer({ version, payload });
  const state = {
    id,
    local: { revision: 0, payload: clone(payload) },
    remote: { version, payload: clone(payload) },
    ...emptyControlState(),
  };
  assertValid(state);
  return state;
}

export function statusOf(state) {
  assertValid(state);
  if (state.conflict) return "conflict";
  if (state.active) return "syncing";
  if (state.blocked) return "blocked-auth";
  if (state.terminal) return "permanent-failure";
  if (state.retry) return "retry-wait";
  if (state.queued) return "pending";
  return "synced";
}

export function editRecord(state, { commandId, patch }) {
  assertValid(state);
  if (state.conflict) {
    throw new Error("resolve the conflict before editing");
  }
  if (!patch || typeof patch !== "object" || Array.isArray(patch)) {
    throw new Error("patch must be an object");
  }

  const revision = state.local.revision + 1;
  const payload = { ...clone(state.local.payload), ...clone(patch) };
  validatePayload(payload);
  const next = {
    ...clone(state),
    local: { revision, payload },
    // Only a never-attempted queued upsert is coalesced. active/retry/blocked/
    // terminal snapshots stay byte-for-byte stable.
    queued: command({
      commandId,
      localRevision: revision,
      baseVersion: state.remote?.version ?? null,
      payload,
    }),
    lastError: null,
  };
  assertValid(next);
  return next;
}

export function startNext(state) {
  assertValid(state);
  if (state.conflict || state.active || state.blocked || state.terminal) {
    return clone(state);
  }

  const selected = state.retry ?? state.queued;
  if (!selected) {
    return clone(state);
  }

  const next = {
    ...clone(state),
    active: clone(selected),
    retry: null,
    queued: state.retry ? clone(state.queued) : null,
    lastError: null,
  };
  assertValid(next);
  return next;
}

export function syncSucceeded(state, { commandId, server }) {
  assertValid(state);
  if (!state.active || state.active.commandId !== commandId) {
    return clone(state);
  }
  validateServerTransition(state, server);

  const active = state.active;
  const hasNewerLocal = state.local.revision > active.localRevision;
  let queued = clone(state.queued);
  let local = clone(state.local);

  if (!hasNewerLocal && !queued) {
    local = {
      revision: state.local.revision,
      payload: clone(server.payload),
    };
  } else {
    if (!queued) {
      throw new Error("newer local revision must have a queued command");
    }
    // queued has never been attempted, so it can be rebased. The completed
    // active command snapshot is never edited in place.
    queued = command({
      ...queued,
      localRevision: state.local.revision,
      baseVersion: server.version,
      payload: state.local.payload,
    });
  }

  const next = {
    ...clone(state),
    local,
    remote: { version: server.version, payload: clone(server.payload) },
    active: null,
    queued,
    lastError: null,
  };
  assertValid(next);
  return next;
}

export function syncFailed(
  state,
  { commandId, reason, classification = "retryable" },
) {
  assertValid(state);
  if (!state.active || state.active.commandId !== commandId) {
    return clone(state);
  }
  if (!new Set(["retryable", "blocked-auth", "permanent"]).has(classification)) {
    throw new Error("unknown failure classification");
  }
  if (typeof reason !== "string" || reason === "") {
    throw new Error("failure reason is required");
  }

  const attempted = clone(state.active);
  const next = {
    ...clone(state),
    active: null,
    retry: classification === "retryable" ? attempted : null,
    blocked:
      classification === "blocked-auth" ? { command: attempted, reason } : null,
    terminal:
      classification === "permanent" ? { command: attempted, reason } : null,
    lastError: { reason, classification },
  };
  assertValid(next);
  return next;
}

export function resumeAfterAuthentication(state) {
  assertValid(state);
  if (!state.blocked) {
    throw new Error("no authentication-blocked command");
  }
  const next = {
    ...clone(state),
    retry: clone(state.blocked.command),
    blocked: null,
    lastError: null,
  };
  assertValid(next);
  return next;
}

export function replacePermanentFailure(state, { commandId }) {
  assertValid(state);
  if (!state.terminal) {
    throw new Error("no permanent failure to replace");
  }
  const next = {
    ...clone(state),
    terminal: null,
    queued:
      state.queued ??
      command({
        commandId,
        localRevision: state.local.revision,
        baseVersion: state.remote?.version ?? null,
        payload: state.local.payload,
      }),
    lastError: null,
  };
  assertValid(next);
  return next;
}

export function syncConflicted(state, { commandId, server }) {
  assertValid(state);
  if (!state.active || state.active.commandId !== commandId) {
    return clone(state);
  }
  validateServerTransition(state, server);

  const next = {
    ...clone(state),
    remote: { version: server.version, payload: clone(server.payload) },
    active: null,
    retry: null,
    queued: null,
    blocked: null,
    terminal: null,
    conflict: {
      commandId,
      baseVersion: state.active.baseVersion,
      local: clone(state.local.payload),
      remote: { version: server.version, payload: clone(server.payload) },
    },
    lastError: null,
  };
  assertValid(next);
  return next;
}

export function resolveWithRemote(state) {
  assertValid(state);
  if (!state.conflict || !state.remote) {
    throw new Error("no conflict to resolve");
  }

  const next = {
    ...clone(state),
    local: {
      revision: state.local.revision + 1,
      payload: clone(state.remote.payload),
    },
    ...emptyControlState(),
    remote: clone(state.remote),
  };
  assertValid(next);
  return next;
}

export function resolveWithLocal(state, { commandId }) {
  return resolveWithPayload(state, { commandId, payload: state.local?.payload });
}

export function resolveWithMerged(state, { commandId, payload }) {
  return resolveWithPayload(state, { commandId, payload });
}

function resolveWithPayload(state, { commandId, payload }) {
  assertValid(state);
  if (!state.conflict || !state.remote) {
    throw new Error("no conflict to resolve");
  }
  validatePayload(payload);

  const revision = state.local.revision + 1;
  const next = {
    ...clone(state),
    local: { revision, payload: clone(payload) },
    active: null,
    retry: null,
    blocked: null,
    terminal: null,
    queued: command({
      commandId,
      localRevision: revision,
      baseVersion: state.remote.version,
      payload,
    }),
    conflict: null,
    lastError: null,
  };
  assertValid(next);
  return next;
}

export function assertValid(state) {
  if (!state || typeof state !== "object") {
    throw new Error("state is required");
  }
  if (typeof state.id !== "string" || state.id === "") {
    throw new Error("record id is required");
  }
  if (!Number.isInteger(state.local?.revision) || state.local.revision < 0) {
    throw new Error("local revision must be a non-negative integer");
  }
  validatePayload(state.local.payload);
  if (state.remote) {
    validateServer(state.remote);
  }

  const nonExecutable = [state.conflict, state.blocked, state.terminal].filter(Boolean);
  if (nonExecutable.length > 1) {
    throw new Error("conflict, auth block and permanent failure are exclusive");
  }
  if (state.conflict && (state.active || state.retry || state.queued)) {
    throw new Error("conflict cannot coexist with executable commands");
  }
  if ((state.blocked || state.terminal) && (state.active || state.retry)) {
    throw new Error("blocked commands cannot be active or retrying");
  }

  const commands = [
    state.active,
    state.retry,
    state.queued,
    state.blocked?.command,
    state.terminal?.command,
  ].filter(Boolean);
  const ids = commands.map((item) => item.commandId);
  if (ids.length !== new Set(ids).size) {
    throw new Error("command identities must be unique across slots");
  }
  for (const item of commands) {
    command(item);
    if (item.localRevision > state.local.revision) {
      throw new Error("command cannot reference a future local revision");
    }
  }
  if (state.queued && state.queued.localRevision !== state.local.revision) {
    throw new Error("queued command must describe the latest local revision");
  }
  return true;
}

function validateServerTransition(state, server) {
  validateServer(server);
  if (state.remote && server.version < state.remote.version) {
    throw new Error("server version regression");
  }
}

function validateServer(server) {
  if (!server || !Number.isInteger(server.version) || server.version < 0) {
    throw new Error("server version must be a non-negative integer");
  }
  validatePayload(server.payload);
}
