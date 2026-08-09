import { fireEvent, render } from "@testing-library/react-native";
import { RecordForm } from "../src/components/RecordForm";

describe("Stage 01 learner form contract", () => {
  it("rejects an empty title with an observable error and preserves the draft", async () => {
    const onSubmit = jest.fn();
    const view = await render(<RecordForm onSubmit={onSubmit} />);
    await fireEvent.press(view.getByRole("button", { name: "저장" }));
    // Intentionally absent in the skeleton: add an accessible validation error.
    expect(view.getByRole("alert")).toHaveTextContent("제목을 입력하세요.");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
