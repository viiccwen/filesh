import { useEffect } from "react";
import { Outlet } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Toaster } from "@/components/ui/sonner";
import { useAuthStore } from "@/features/auth/store";

export function AppShell() {
  const bootstrap = useAuthStore((state) => state.bootstrap);
  const status = useAuthStore((state) => state.status);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <Card className="rounded-[2rem] border-border/70 bg-card/90 shadow-sm backdrop-blur">
          <CardHeader className="gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <Badge variant="outline">filesh</Badge>
              <Badge
                variant={status === "authenticated" ? "default" : "secondary"}
              >
                {status === "authenticated"
                  ? "Authenticated"
                  : status === "booting"
                    ? "Booting"
                    : "Guest"}
              </Badge>
            </div>
            <CardTitle className="text-4xl leading-none sm:text-5xl">
              Spec-driven file sharing frontend
            </CardTitle>
            <CardDescription className="max-w-3xl text-base leading-7">
              This pass fixes the app structure around routing, page boundaries,
              zustand, and zod so we do not need to split it apart again later.
            </CardDescription>
          </CardHeader>
        </Card>

        <Outlet />
      </div>
      <Toaster richColors />
    </div>
  );
}
