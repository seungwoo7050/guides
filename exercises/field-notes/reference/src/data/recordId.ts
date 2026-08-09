let nextRecordNumber = 1;

export function nextInMemoryRecordId(): string {
  const value = `new-record-${String(nextRecordNumber).padStart(3, "0")}`;
  nextRecordNumber += 1;
  return value;
}

