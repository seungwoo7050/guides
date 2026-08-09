import { Page } from "../../../src/components/Page";
import { RecordForm } from "../../../src/components/RecordForm";
import { TodoNotice } from "../../../src/components/TodoNotice";

export default function EditRoute() {
  return (
    <Page title="기록 편집 TODO">
      <TodoNotice title="의도적으로 미완성">
        fixture 조회, validation, stale revision, unsaved back 처리를 구현하세요.
      </TodoNotice>
      <RecordForm onSubmit={() => {}} />
    </Page>
  );
}

