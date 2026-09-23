import type { ReactNode } from "react";

import { TopNav } from "@/components/chrome/top-nav";
import { Footer } from "@/components/chrome/footer";

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <TopNav />
      <main id="main" className="flex-1">
        {children}
      </main>
      <Footer />
    </div>
  );
}
