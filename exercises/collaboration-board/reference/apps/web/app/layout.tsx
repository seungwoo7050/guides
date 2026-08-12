import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "협업 보드",
  description: "실시간 협업 보드 학습 예제"
};

// [Implementation 6-1]
// root layout이 document 언어, metadata와 본문 건너뛰기 진입점을 소유해 모든 page가 같은 접근성 기반을 상속합니다.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ko">
    <body>
      <a className="skip-link" href="#main">본문으로 건너뛰기</a>
      {children}
    </body>
  </html>;
}
