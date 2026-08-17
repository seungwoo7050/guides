import Link from "next/link";
import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return <>
    <header className="site-header">
      <Link className="brand" href="/">Collaboration Board</Link>
      <nav aria-label="Primary navigation">
        <Link href="/">Boards</Link>
        <Link href="/activity">Activity</Link>
        <Link href="/admin">Admin</Link>
      </nav>
    </header>
    {children}
  </>;
}
