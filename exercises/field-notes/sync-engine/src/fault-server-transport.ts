import { DeterministicFaultServer } from "../../fault-server/src/index.ts";
import type { SyncTransport } from "./ports.ts";
import type { RecordCommand, WireResponse } from "./types.ts";

function abortError(): Error {
  const error = new Error("sync transport aborted before send");
  error.name = "AbortError";
  return error;
}

/** In-process adapter; production HTTP authentication is intentionally absent. */
export class FaultServerTransport implements SyncTransport {
  readonly #server: DeterministicFaultServer;

  constructor(server: DeterministicFaultServer) {
    this.#server = server;
  }

  async send(command: RecordCommand, signal: AbortSignal): Promise<WireResponse> {
    if (signal.aborted) {
      throw abortError();
    }
    return this.#server.execute(command);
  }
}
