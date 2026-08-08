import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "협업 보드",
  description: "실시간 협업 보드 학습 예제"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ko">
    <body>
      <a className="skip-link" href="#main">본문으로 건너뛰기</a>
      {children}
    </body>
  </html>;
}
