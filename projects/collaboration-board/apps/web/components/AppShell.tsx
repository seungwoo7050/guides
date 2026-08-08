import Link from "next/link";

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
