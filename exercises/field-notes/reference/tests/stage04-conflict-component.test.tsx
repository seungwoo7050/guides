import type { DurableConflict } from "@field-notes/sync-engine";
import { fireEvent, render, waitFor } from "@testing-library/react-native";
import { ConflictResolutionCard } from "../src/components/ConflictResolutionCard";

const conflict: DurableConflict = {
  conflictId: "conflict-1",
  commandId: "command-1",
  recordId: "record-1",
  attempted: {
    commandId: "command-1",
    recordId: "record-1",
    operation: "upsert",
    baseVersion: 3,
    localRevision: 4,
    payload: {
      title: "attempted title",
      notes: "attempted notes",
      status: "open",
      observedAt: "2026-08-09T10:00:00.000Z",
    },
    createdAt: "2026-08-09T10:01:00.000Z",
  },
  local: {
    localRevision: 5,
    payload: {
      title: "local title",
      notes: "local notes",
      status: "draft",
      observedAt: "2026-08-09T11:00:00.000Z",
      location: {
        latitude: 37,
        longitude: 127,
        accuracyMeters: 20,
        measuredAt: "2026-08-09T11:00:01.000Z",
      },
    },
  },
  remote: {
    recordId: "record-1",
    version: 4,
    deleted: false,
    payload: {
      title: "remote title",
      notes: "remote notes",
      status: "resolved",
      observedAt: "2026-08-09T12:00:00.000Z",
      location: {
        latitude: 35,
        longitude: 129,
        accuracyMeters: 8,
        measuredAt: "2026-08-09T12:00:01.000Z",
      },
    },
  },
  createdAt: 1,
};

describe("Stage 04 conflict evidence and merge UI", () => {
  it("shows all payload fields for attempted/local/remote and submits an explicit field merge", async () => {
    const onResolve = jest.fn().mockResolvedValue(undefined);
    const view = await render(
      <ConflictResolutionCard conflict={conflict} onResolve={onResolve} />,
    );
    expect(view.getByText("attempted / base v3")).toBeTruthy();
    expect(view.getByText(/notes: attempted notes/)).toBeTruthy();
    expect(view.getByText(/status: draft/)).toBeTruthy();
    expect(view.getByText(/observedAt: 2026-08-09T12:00:00.000Z/)).toBeTruthy();
    expect(view.getByText(/location: 35, 129/)).toBeTruthy();

    await fireEvent.press(view.getByRole("radio", { name: "병합 위치: remote" }));
    await fireEvent.changeText(view.getByLabelText("기록 제목"), "merged title");
    await fireEvent.press(view.getByRole("button", { name: "필드 병합 command 생성" }));
    await waitFor(() => {
      expect(onResolve).toHaveBeenCalledWith(
        "merge",
        expect.objectContaining({
          title: "merged title",
          notes: "local notes",
          status: "draft",
          observedAt: "2026-08-09T11:00:00.000Z",
          location: conflict.remote?.payload?.location,
        }),
      );
    });
  });
});
