import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "../components/AppShell";
import "./globals.css";

// [Implementation 9] Establish the browser document, navigation shell, and global presentation boundary before feature components acquire client state.
export const metadata: Metadata = {
  title: "Collaboration Board",
  description: "Realtime collaborative board with explicit persistence and authorization boundaries"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="en"><body><AppShell>{children}</AppShell></body></html>;
}
