import { AppShell } from "../components/AppShell";
import { BoardList } from "../components/BoardList";

// [Implementation 6-6]
// root route는 reusable shell과 board feature를 결합할 뿐, feature state나 HTTP 호출을 다시 소유하지 않습니다.
export default function Page() {
  return <AppShell><BoardList /></AppShell>;
}
