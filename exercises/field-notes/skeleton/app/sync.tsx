import { Page } from "../src/components/Page";
import { TodoNotice } from "../src/components/TodoNotice";

export default function SyncRoute() {
  return <Page title="동기화 TODO"><TodoNotice title="Stage 04 범위">Stage 01에서는 SyncTransport나 outbox를 구현하지 않습니다.</TodoNotice></Page>;
}

