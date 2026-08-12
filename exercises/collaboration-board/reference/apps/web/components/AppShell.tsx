import Link from "next/link";

// [Implementation 6-2]
// shell은 route마다 복제하기 쉬운 navigation과 main landmark를 한 곳에서 소유합니다.
// feature component는 이 경계 안에서 자신의 loading·error·domain state에만 집중합니다.
export function AppShell({ children }: { children: React.ReactNode }) {
  return <>
    <header className="border-b border-slate-200 bg-white">
      <nav
        aria-label="주 메뉴"
        className="mx-auto flex w-[min(72rem,calc(100%-2rem))] items-center justify-between py-4"
      >
        <Link className="focus-ring text-xl font-black" href="/">협업 보드</Link>
        <div className="flex gap-4 text-sm font-bold">
          <Link href="/">내 보드</Link>
          <Link href="/activity">활동 기록</Link>
          <Link href="/admin">관리</Link>
        </div>
      </nav>
    </header>
    <main
      id="main"
      tabIndex={-1}
      className="mx-auto w-[min(72rem,calc(100%-2rem))] py-8"
    >
      {children}
    </main>
  </>;
}
