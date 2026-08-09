import { FIELD_RECORD_FIXTURES } from "@field-notes/shared";
import { fireEvent, render, waitFor } from "@testing-library/react-native";
import { RecordForm, TITLE_LIMIT } from "../src/components/RecordForm";
import { RecordListItem } from "../src/components/RecordListItem";

describe("Stage 01 accessible components", () => {
  it("gives a record card a button role and meaningful label", async () => {
    const onPress = jest.fn();
    const view = await render(<RecordListItem onPress={onPress} record={FIELD_RECORD_FIXTURES[0]!} />);
    const item = view.getByRole("button", {
      name: "숲 가장자리 토양 상태, 진행 중",
    });
    await fireEvent.press(item);
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it("keeps a long draft visible, exposes an error, and does not submit", async () => {
    const onSubmit = jest.fn();
    const view = await render(<RecordForm onCancel={jest.fn()} onSubmit={onSubmit} />);
    const title = view.getByLabelText("기록 제목");
    const longTitle = "가".repeat(TITLE_LIMIT + 1);
    await fireEvent.changeText(title, longTitle);
    await fireEvent.press(view.getByRole("button", { name: "저장" }));
    expect(view.getByRole("alert")).toHaveTextContent(
      `제목은 ${TITLE_LIMIT}자 이하여야 합니다.`,
    );
    expect(view.getByLabelText("기록 제목")).toHaveProp("value", longTitle);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("labels status choices and submits normalized valid behavior", async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    const view = await render(<RecordForm onCancel={jest.fn()} onSubmit={onSubmit} />);
    await fireEvent.changeText(view.getByLabelText("기록 제목"), "  새 관찰  ");
    await fireEvent.changeText(view.getByLabelText("기록 메모"), "  상세 메모  ");
    await fireEvent.press(view.getByRole("radio", { name: "상태: 진행 중" }));
    expect(view.getByRole("radio", { name: "상태: 진행 중, 선택됨" })).toHaveProp(
      "accessibilityState",
      expect.objectContaining({ checked: true }),
    );
    await fireEvent.press(view.getByRole("button", { name: "저장" }));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "새 관찰",
          notes: "상세 메모",
          status: "open",
        }),
      );
    });
  });

  it("reports dirty-state transitions needed by the system back guard", async () => {
    const onDirtyChange = jest.fn();
    const view = await render(
      <RecordForm
        onCancel={jest.fn()}
        onDirtyChange={onDirtyChange}
        onSubmit={jest.fn()}
      />,
    );
    await fireEvent.changeText(view.getByLabelText("기록 메모"), "draft survives validation");
    expect(onDirtyChange).toHaveBeenLastCalledWith(true);
  });
});
