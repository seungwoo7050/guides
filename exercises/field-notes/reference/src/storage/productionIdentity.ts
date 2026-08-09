import type { Clock, IdGenerator } from "@field-notes/shared";

let sequence = 0;

function nextId(prefix: string): string {
  sequence += 1;
  const random = Math.random().toString(36).slice(2, 10);
  return `${prefix}-${Date.now().toString(36)}-${sequence.toString(36)}-${random}`;
}

export const productionClock: Clock = {
  now: () => new Date().toISOString(),
};
export const productionIds: IdGenerator = {
  recordId: () => nextId("record"),
  attachmentId: () => nextId("attachment"),
  commandId: () => nextId("command"),
};
