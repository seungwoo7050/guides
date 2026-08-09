export type ExpoNotificationResponseShape = {
  actionIdentifier: string;
  notification: {
    request: {
      identifier: string;
    };
  };
};

export interface ExpoNotificationResponseApi<Response> {
  getLastNotificationResponse(): Response | null;
  addNotificationResponseReceivedListener(
    listener: (response: Response) => void,
  ): { remove(): void };
  clearLastNotificationResponse(): void;
}

export type DurableNotificationResponseDisposition =
  | { kind: "acknowledged" }
  | { kind: "terminal"; code: string }
  | { kind: "retryable"; code: string };

export interface DurableNotificationResponseHandler<Response> {
  /**
   * A clear failure permits the same native response to be offered again.
   * Implementations must use the parsed messageId's durable claim/terminal
   * state so acknowledged and terminal replays are idempotent.
   */
  handle(response: Response): Promise<DurableNotificationResponseDisposition>;
}

export type NotificationResponseOrigin = "cold" | "warm";
export type NotificationResponseClearState = "cleared" | "not-current";

export type NotificationResponseProcessingResult =
  | {
      kind: "acknowledged";
      origin: NotificationResponseOrigin;
      responseLabel: string;
      clear: NotificationResponseClearState;
    }
  | {
      kind: "terminal";
      origin: NotificationResponseOrigin;
      responseLabel: string;
      code: string;
      clear: NotificationResponseClearState;
    }
  | {
      kind: "retryable";
      origin: NotificationResponseOrigin;
      responseLabel: string;
      code: string;
    }
  | {
      kind: "duplicate";
      origin: NotificationResponseOrigin;
      responseLabel: string;
    }
  | {
      kind: "invalid-response";
      origin: NotificationResponseOrigin;
      responseLabel: string;
    }
  | {
      kind: "handler-error";
      origin: NotificationResponseOrigin;
      responseLabel: string;
      code: "handler-threw";
    }
  | {
      kind: "clear-error";
      origin: NotificationResponseOrigin;
      responseLabel: string;
      disposition: "acknowledged" | "terminal";
      code: "clear-failed";
    };

export type NotificationResponseSourceStartResult =
  | {
      kind: "started";
      cold: NotificationResponseProcessingResult | null;
    }
  | { kind: "already-started" }
  | {
      kind: "source-error";
      stage: "listener-registration" | "cold-read";
    };

function safeCode(value: string, fallback: string): string {
  return /^[a-z0-9][a-z0-9._:-]{0,63}$/.test(value) ? value : fallback;
}

/** Uses native request/action identity only; content.data is never inspected. */
export function expoNotificationResponseKey(
  response: ExpoNotificationResponseShape,
): string {
  const requestId = response.notification?.request?.identifier;
  const actionId = response.actionIdentifier;
  if (
    typeof requestId !== "string" ||
    requestId.length === 0 ||
    requestId.length > 512 ||
    typeof actionId !== "string" ||
    actionId.length === 0 ||
    actionId.length > 512
  ) {
    throw new TypeError("notification response has no bounded native identity");
  }
  return JSON.stringify([requestId, actionId]);
}

/**
 * Subscribes before reading the cold response, then sends cold and warm values
 * through one queue. Clear is attempted only after the durable handler returns
 * acknowledged/terminal and only when the handled response is still native-last.
 * A clear error is not remembered: a later delivery re-enters the handler so it
 * can consult its durable messageId claim and retry native clear safely.
 */
export class SerializedExpoNotificationResponseSource<Response> {
  readonly #api: ExpoNotificationResponseApi<Response>;
  readonly #handler: DurableNotificationResponseHandler<Response>;
  readonly #keyOf: (response: Response) => string;
  readonly #onResult: (result: NotificationResponseProcessingResult) => void;
  readonly #active = new Set<string>();
  readonly #remembered = new Set<string>();
  readonly #rememberedOrder: string[] = [];
  readonly #labels = new Map<string, string>();
  #tail: Promise<void> = Promise.resolve();
  #subscription: { remove(): void } | null = null;
  #started = false;

  constructor(input: {
    api: ExpoNotificationResponseApi<Response>;
    handler: DurableNotificationResponseHandler<Response>;
    keyOf: (response: Response) => string;
    onResult?: (result: NotificationResponseProcessingResult) => void;
  }) {
    this.#api = input.api;
    this.#handler = input.handler;
    this.#keyOf = input.keyOf;
    this.#onResult = input.onResult ?? (() => undefined);
  }

  async start(): Promise<NotificationResponseSourceStartResult> {
    if (this.#started) return { kind: "already-started" };
    this.#started = true;
    try {
      this.#subscription = this.#api.addNotificationResponseReceivedListener(
        (response) => {
          void this.enqueue("warm", response);
        },
      );
    } catch {
      this.#started = false;
      return { kind: "source-error", stage: "listener-registration" };
    }

    let cold: Response | null;
    try {
      cold = this.#api.getLastNotificationResponse();
    } catch {
      this.#stopSubscription();
      this.#started = false;
      return { kind: "source-error", stage: "cold-read" };
    }
    return {
      kind: "started",
      cold: cold === null ? null : await this.enqueue("cold", cold),
    };
  }

  stop(): void {
    this.#stopSubscription();
    this.#started = false;
  }

  async whenIdle(): Promise<void> {
    await this.#tail;
  }

  async enqueue(
    origin: NotificationResponseOrigin,
    response: Response,
  ): Promise<NotificationResponseProcessingResult> {
    let key: string;
    try {
      key = this.#validatedKey(response);
    } catch {
      return this.#publish({
        kind: "invalid-response",
        origin,
        responseLabel: "response#invalid",
      });
    }
    const responseLabel = this.#labelFor(key);
    if (this.#active.has(key) || this.#remembered.has(key)) {
      return this.#publish({
        kind: "duplicate",
        origin,
        responseLabel,
      });
    }
    this.#active.add(key);

    const preceding = this.#tail;
    let release!: () => void;
    this.#tail = new Promise<void>((resolve) => {
      release = resolve;
    });
    await preceding;

    let result: NotificationResponseProcessingResult;
    try {
      result = await this.#process(origin, responseLabel, key, response);
      if (result.kind === "acknowledged" || result.kind === "terminal") {
        this.#remember(key);
      }
    } catch {
      result = {
        kind: "handler-error",
        origin,
        responseLabel,
        code: "handler-threw",
      };
    } finally {
      this.#active.delete(key);
      release();
    }
    return this.#publish(result);
  }

  async #process(
    origin: NotificationResponseOrigin,
    responseLabel: string,
    key: string,
    response: Response,
  ): Promise<NotificationResponseProcessingResult> {
    let disposition: DurableNotificationResponseDisposition;
    try {
      disposition = await this.#handler.handle(response);
    } catch {
      return {
        kind: "handler-error",
        origin,
        responseLabel,
        code: "handler-threw",
      };
    }
    if (disposition.kind === "retryable") {
      return {
        kind: "retryable",
        origin,
        responseLabel,
        code: safeCode(disposition.code, "retryable"),
      };
    }

    let clear: NotificationResponseClearState;
    try {
      const current = this.#api.getLastNotificationResponse();
      if (current === null || this.#validatedKey(current) !== key) {
        clear = "not-current";
      } else {
        this.#api.clearLastNotificationResponse();
        clear = "cleared";
      }
    } catch {
      return {
        kind: "clear-error",
        origin,
        responseLabel,
        disposition: disposition.kind,
        code: "clear-failed",
      };
    }

    if (disposition.kind === "terminal") {
      return {
        kind: "terminal",
        origin,
        responseLabel,
        code: safeCode(disposition.code, "terminal"),
        clear,
      };
    }
    return { kind: "acknowledged", origin, responseLabel, clear };
  }

  #validatedKey(response: Response): string {
    const key = this.#keyOf(response);
    if (typeof key !== "string" || key.length === 0 || key.length > 2_048) {
      throw new TypeError("notification response key must be bounded");
    }
    return key;
  }

  #labelFor(key: string): string {
    const current = this.#labels.get(key);
    if (current !== undefined) return current;
    const label = `response#${this.#labels.size + 1}`;
    this.#labels.set(key, label);
    return label;
  }

  #remember(key: string): void {
    this.#remembered.add(key);
    this.#rememberedOrder.push(key);
    if (this.#rememberedOrder.length <= 256) return;
    const oldest = this.#rememberedOrder.shift();
    if (oldest !== undefined) this.#remembered.delete(oldest);
  }

  #publish(
    result: NotificationResponseProcessingResult,
  ): NotificationResponseProcessingResult {
    try {
      this.#onResult(result);
    } catch {
      // Observation is non-authoritative and cannot break durable processing.
    }
    return result;
  }

  #stopSubscription(): void {
    const subscription = this.#subscription;
    this.#subscription = null;
    if (subscription === null) return;
    try {
      subscription.remove();
    } catch {
      // Listener teardown cannot undo an already durable disposition.
    }
  }
}
