import {
  ArrowRightIcon,
  CloudUploadIcon,
  FolderTreeIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuthStore } from "@/features/auth/store";
import { getInitials } from "@/lib/format";

const featureCards = [
  {
    description:
      "Keep nested folders, uploads, and fast navigation inside one calm workspace.",
    icon: FolderTreeIcon,
    title: "Structured file work",
  },
  {
    description:
      "Share folders with guest links, invited emails, or signed-in collaborators.",
    icon: ShieldCheckIcon,
    title: "Policy-based sharing",
  },
  {
    description:
      "Move from upload to distribution without losing visibility over what changed.",
    icon: CloudUploadIcon,
    title: "Reliable delivery flow",
  },
];

const productStats = [
  { label: "Access modes", value: "3" },
  { label: "Max file size", value: "50 MB" },
  { label: "Workspace flows", value: "Search, sort, share" },
];

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

        <main className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="relative overflow-hidden rounded-[2.5rem] border border-border/70 bg-card/85 px-6 py-8 shadow-xl shadow-black/5 sm:px-8 sm:py-10">
            <div className="absolute inset-x-0 top-0 h-40 bg-linear-to-br from-primary/10 via-transparent to-chart-2/12" />
            <div className="absolute -right-12 top-14 size-40 rounded-full bg-chart-1/35 blur-3xl" />
            <div className="absolute bottom-6 left-8 size-32 rounded-full bg-primary/8 blur-3xl" />

            <div className="relative flex flex-col gap-7">
              <div className="flex flex-wrap items-center gap-3">
                <Badge className="rounded-full px-3 py-1" variant="outline">
                  Product landing
                </Badge>
                <Badge className="rounded-full px-3 py-1" variant="secondary">
                  Workspace-first sharing
                </Badge>
              </div>

              <div className="max-w-3xl">
                <h1 className="max-w-3xl text-5xl leading-none tracking-[-0.06em] text-balance text-foreground sm:text-6xl lg:text-7xl">
                  filesh keeps file sharing clear, fast, and controlled.
                </h1>
                <p className="mt-5 max-w-2xl text-base leading-8 text-muted-foreground sm:text-lg">
                  Bring uploads, nested folders, and share policies into one
                  focused workspace. filesh helps teams move from delivery to
                  access without the usual friction.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
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

              <div className="grid gap-3 sm:grid-cols-3">
                {productStats.map((stat) => (
                  <div
                    className="rounded-[1.75rem] border border-border/70 bg-background/75 px-4 py-4 backdrop-blur"
                    key={stat.label}
                  >
                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                      {stat.label}
                    </p>
                    <p className="mt-2 text-xl font-semibold text-foreground">
                      {stat.value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="grid gap-4">
            <Card className="overflow-hidden rounded-[2.25rem] border-border/70 bg-card/88 shadow-lg shadow-black/5">
              <CardContent className="flex flex-col gap-6 p-6 sm:p-7">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted-foreground">
                      Live surface
                    </p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
                      Built for real file operations
                    </h2>
                  </div>
                  <Avatar className="size-12 border border-border/70 bg-secondary">
                    <AvatarFallback>
                      {isAuthenticated ? getInitials(user.nickname) : "FS"}
                    </AvatarFallback>
                  </Avatar>
                </div>

                <div className="grid gap-3">
                  {featureCards.map((feature) => (
                    <div
                      className="rounded-[1.5rem] border border-border/70 bg-background/80 p-4"
                      key={feature.title}
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-secondary text-foreground">
                          <feature.icon />
                        </div>
                        <div>
                          <h3 className="text-base font-medium text-foreground">
                            {feature.title}
                          </h3>
                          <p className="mt-1 text-sm leading-6 text-muted-foreground">
                            {feature.description}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card className="rounded-[2.25rem] border-border/70 bg-foreground text-background shadow-lg shadow-black/5">
              <CardContent className="flex flex-col gap-4 p-6 sm:p-7">
                <Badge className="w-fit rounded-full bg-background/10 px-3 py-1 text-background hover:bg-background/10">
                  Product promise
                </Badge>
                <p className="text-2xl font-semibold tracking-tight text-balance">
                  Stop stitching together uploads, links, and permissions across
                  too many tools.
                </p>
                <p className="text-sm leading-7 text-background/72">
                  filesh is designed to feel like one product from landing to
                  workspace, with the same clarity in navigation, sharing, and
                  access control.
                </p>
              </CardContent>
            </Card>
          </section>
        </main>
      </div>
    </div>
  );
}
