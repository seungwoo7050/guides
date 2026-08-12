import type { Metadata } from "next";
import "./style.css";

// [Implementation 1] server root layout이 문서 언어·metadata와 전역 style의 소유 경계를 먼저 정합니다.
export const metadata: Metadata = { title: "Frontend Exercise", description: "React state and effect exercise" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}
