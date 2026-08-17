import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./style.css";

// [Implementation 1] Establish document language, metadata, and global-style ownership at the server root layout.
export const metadata: Metadata = {
  title: "User Directory",
  description: "Abortable user search with a dynamic profile route"
};

export default function Layout({ children }: { children: ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
