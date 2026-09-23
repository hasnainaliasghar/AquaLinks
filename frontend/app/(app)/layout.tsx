import type { ReactNode } from "react";

import { AppSidebar, MobileTabBar } from "@/components/chrome/app-sidebar";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <AppSidebar />
      <div className="flex min-h-screen flex-1 flex-col">
        <main id="main" className="flex-1 pb-20 lg:pb-0">
          {children}
        </main>
        <MobileTabBar />
      </div>
    </div>
  );
}
