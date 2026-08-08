import { AppShell } from "../../components/AppShell";

export default function ActivityPage() {
  return <AppShell>
    <h1 className="text-3xl font-black">활동 기록</h1>
    <p className="mt-4 text-slate-600">
      각 보드의 활동 기록은 <code>GET /boards/:id/activity</code>로 조회합니다.
      편집 완료 이벤트만 영속화하므로 드래그 중간 좌표는 기록을 불필요하게 늘리지 않습니다.
    </p>
  </AppShell>;
}
