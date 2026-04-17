import { ArrowRightIcon, SparklesIcon } from "lucide-react";
import { Link } from "react-router-dom";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/features/auth/store";
import { getInitials } from "@/lib/format";

export function LandingPage() {
  const status = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);

  const isAuthenticated = status === "authenticated" && user;
  const primaryHref = isAuthenticated ? "/app" : "/register";
  const primaryLabel = isAuthenticated ? "Open workspace" : "Start with filesh";

  return (
    <div className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 pb-10 pt-2 sm:gap-10 sm:pb-14">
        <header className="sticky top-4 z-40">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 rounded-full border border-border/70 bg-background/78 px-3 py-3 shadow-lg shadow-black/5 ring-1 ring-white/55 backdrop-blur-xl sm:px-5">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-full bg-foreground text-background">
                <SparklesIcon />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold tracking-[0.22em] text-foreground uppercase">
                  filesh
                </p>
                <p className="text-xs text-muted-foreground">
                  Share files like a real product, not a folder dump.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 sm:gap-3">
              {isAuthenticated ? (
                <>
                  <Button asChild variant="ghost">
                    <Link to="/app">Workspace</Link>
                  </Button>
                  <Avatar className="size-10 border border-border/70 bg-card">
                    <AvatarFallback>
                      {getInitials(user.nickname)}
                    </AvatarFallback>
                  </Avatar>
                </>
              ) : (
                <>
                  <Button
                    asChild
                    className="hidden sm:inline-flex"
                    variant="ghost"
                  >
                    <Link to="/login">Login</Link>
                  </Button>
                  <Button asChild>
                    <Link to="/register">Register</Link>
                  </Button>
                  <Avatar className="size-10 border border-border/70 bg-card">
                    <AvatarFallback>FS</AvatarFallback>
                  </Avatar>
                </>
              )}
            </div>
          </div>
        </header>

        <main className="relative flex min-h-[calc(100vh-8rem)] items-center justify-center overflow-hidden rounded-[2.75rem] px-4 py-16 sm:px-8 sm:py-24">
          <div className="absolute inset-x-0 top-0 h-48 bg-linear-to-br from-primary/10 via-transparent to-chart-2/12" />
          <div className="absolute left-1/2 top-12 size-72 -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
          <div className="absolute right-0 top-24 size-64 rounded-full bg-chart-1/30 blur-3xl" />
          <div className="absolute bottom-0 left-10 size-56 rounded-full bg-primary/8 blur-3xl" />

          <section className="relative flex max-w-4xl flex-col items-center gap-8 text-center">
            <div>
              <h1 className="mx-auto max-w-4xl text-5xl leading-none tracking-[-0.06em] text-balance text-foreground sm:text-6xl lg:text-7xl">
                filesh keeps file sharing clear, fast, and controlled.
              </h1>
              <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-muted-foreground sm:text-lg">
                Bring uploads, nested folders, and share policies into one
                focused workspace. filesh helps teams move from delivery to
                access without the usual friction.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-center gap-3">
              <Button asChild className="rounded-full px-6">
                <Link to={primaryHref}>
                  {primaryLabel}
                  <ArrowRightIcon data-icon="inline-end" />
                </Link>
              </Button>
              <Button asChild className="rounded-full px-6" variant="outline">
                <Link to="/login">See the sign-in flow</Link>
              </Button>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
