import { Link } from "react-router-dom";

import { AppNavbar, AppNavbarUser } from "@/components/app-navbar";
import { Button } from "@/components/ui/button";
import { LoginCard } from "@/features/auth/components/auth-shell";
import { useAuthStore } from "@/features/auth/store";

export function LoginPage() {
  const user = useAuthStore((state) => state.user);

  return (
    <div className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-8 pb-10 pt-2">
        <AppNavbar innerClassName="max-w-5xl">
          <Button asChild className="hidden sm:inline-flex" variant="ghost">
            <Link to="/register">Register</Link>
          </Button>
          <AppNavbarUser nickname={user?.nickname} />
        </AppNavbar>

        <main className="relative flex min-h-[calc(100vh-10rem)] items-center justify-center overflow-hidden rounded-[2.75rem] px-4 py-16 sm:px-8 sm:py-24">
          <div className="absolute inset-x-0 top-0 h-40 bg-linear-to-br from-primary/10 via-transparent to-chart-2/12" />
          <div className="absolute left-1/2 top-14 size-72 -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
          <div className="absolute bottom-0 left-10 size-56 rounded-full bg-primary/8 blur-3xl" />

          <div className="relative flex w-full max-w-xl flex-col items-center gap-6">
            <div className="text-center">
              <h1 className="text-4xl leading-none tracking-[-0.05em] text-foreground sm:text-5xl">
                Sign in to filesh
              </h1>
              <p className="mt-4 text-sm leading-7 text-muted-foreground sm:text-base">
                Access your workspace, manage folders, and continue where you
                left off.
              </p>
            </div>

            <LoginCard />
          </div>
        </main>
      </div>
    </div>
  );
}
