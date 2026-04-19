import { Link } from "react-router-dom";

import { AppNavbar } from "@/components/app-navbar";
import { Button } from "@/components/ui/button";

const statusCopy = {
  deleted: {
    actionLabel: "Return home",
    description:
      "This resource has been deleted, and the old share link is no longer valid.",
    title: "This resource was deleted",
  },
  expired: {
    actionLabel: "Open filesh",
    description:
      "This share link has expired. Ask the owner for a fresh link if you still need access.",
    title: "This share link expired",
  },
  "not-found": {
    actionLabel: "Return home",
    description: "The requested resource or share link could not be found.",
    title: "We couldn't find that page",
  },
  unauthorized: {
    actionLabel: "Go to login",
    description:
      "You do not currently have permission to access this resource.",
    title: "Access is restricted",
  },
} as const;

export function StatusPage({ kind }: { kind: keyof typeof statusCopy }) {
  const copy = statusCopy[kind];

  return (
    <div className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 pb-10 pt-2">
        <AppNavbar innerClassName="max-w-5xl">
          <Button asChild className="rounded-full" variant="outline">
            <Link to="/">Home</Link>
          </Button>
        </AppNavbar>

        <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center">
          <main className="relative flex w-full max-w-3xl flex-col items-center justify-center overflow-hidden rounded-[2.75rem] border border-border/70 bg-background/80 px-6 py-16 text-center shadow-lg shadow-black/5 ring-1 ring-white/45 backdrop-blur-xl sm:px-10 sm:py-24">
            <div className="absolute inset-x-0 top-0 h-40 bg-linear-to-br from-primary/10 via-transparent to-chart-2/12" />
            <div className="absolute left-1/2 top-10 size-72 -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
            <div className="absolute bottom-0 right-0 size-56 rounded-full bg-chart-1/15 blur-3xl" />

            <div className="relative flex max-w-2xl flex-col items-center gap-6">
              <div className="flex size-18 items-center justify-center"></div>
              <div className="space-y-4">
                <h1 className="text-4xl tracking-[-0.05em] text-foreground sm:text-5xl">
                  {copy.title}
                </h1>
                <p className="text-sm leading-7 text-muted-foreground sm:text-base">
                  {copy.description}
                </p>
              </div>
              <Button asChild className="rounded-full px-6">
                <Link to={kind === "unauthorized" ? "/login" : "/"}>
                  {copy.actionLabel}
                </Link>
              </Button>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
