import type { Metadata } from "next";
import "./style.css";

export const metadata: Metadata = { title: "Frontend Exercise", description: "React state and effect exercise" };

export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}
