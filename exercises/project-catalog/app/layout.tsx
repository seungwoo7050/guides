import type { Metadata } from "next";
import "./styles.css";

// [Implementation 5]
// Application document shell.
export const metadata: Metadata = {
  title: "Project Catalog",
  description: "Searchable project catalog with version-aware editing"
};

export default function Layout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
