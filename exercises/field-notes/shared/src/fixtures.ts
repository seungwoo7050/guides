import type { FieldRecord } from "./contracts";

export const FIELD_RECORD_FIXTURES: readonly FieldRecord[] = [
  {
    id: "forest-edge",
    title: "숲 가장자리 토양 상태",
    notes: "그늘진 구간은 표면 수분이 남아 있다.",
    status: "open",
    observedAt: "2026-08-08T09:30:00.000Z",
    localRevision: 1,
    remoteVersion: null,
    syncState: "local-only",
  },
  {
    id: "harbor-light",
    title: "항구 조명 점검",
    notes: "동쪽 진입로의 두 번째 조명이 간헐적으로 꺼진다.",
    status: "draft",
    observedAt: "2026-08-08T12:15:00.000Z",
    localRevision: 1,
    remoteVersion: null,
    syncState: "local-only",
  },
  {
    id: "ridge-marker",
    title: "능선 표지판",
    notes: "표지판 고정 볼트를 교체했다.",
    status: "resolved",
    observedAt: "2026-08-09T03:05:00.000Z",
    localRevision: 2,
    remoteVersion: null,
    syncState: "local-only",
  },
] as const;

export function cloneFixtureRecords(): FieldRecord[] {
  return FIELD_RECORD_FIXTURES.map((record) => ({ ...record }));
}

