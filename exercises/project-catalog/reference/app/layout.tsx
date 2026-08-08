import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "프로젝트 목록",
  description: "검색과 버전 기반 편집을 제공하는 프로젝트 목록"
};

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
