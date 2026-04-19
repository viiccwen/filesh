import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";

import { useAuthStore } from "@/features/auth/store";
import { Skeleton } from "@/components/ui/skeleton";

const LandingPage = lazy(() =>
  import("@/pages/landing-page").then((module) => ({
    default: module.LandingPage,
  })),
);
const LoginPage = lazy(() =>
  import("@/pages/login-page").then((module) => ({
    default: module.LoginPage,
  })),
);
const RegisterPage = lazy(() =>
  import("@/pages/register-page").then((module) => ({
    default: module.RegisterPage,
  })),
);
const ShareAccessPage = lazy(() =>
  import("@/pages/share-access-page").then((module) => ({
    default: module.ShareAccessPage,
  })),
);
const WorkspacePage = lazy(() =>
  import("@/pages/workspace-page").then((module) => ({
    default: module.WorkspacePage,
  })),
);
const StatusPage = lazy(() =>
  import("@/pages/status-page").then((module) => ({
    default: module.StatusPage,
  })),
);

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((state) => state.status);

  if (status === "booting") {
    return null;
  }

  if (status !== "authenticated") {
    return <Navigate replace to="/login" />;
  }

  return children;
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const status = useAuthStore((state) => state.status);

  if (status === "booting") {
    return null;
  }

  if (status === "authenticated") {
    return <Navigate replace to="/app" />;
  }

  return children;
}

function PageFallback() {
  return (
    <div className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 pb-10 pt-2">
        <Skeleton className="h-16 rounded-full" />
        <Skeleton className="h-40 rounded-[2rem]" />
        <Skeleton className="h-[24rem] rounded-[2rem]" />
      </div>
    </div>
  );
}

function withSuspense(node: React.ReactNode) {
  return <Suspense fallback={<PageFallback />}>{node}</Suspense>;
}

export const router = createBrowserRouter([
  { path: "/", element: withSuspense(<LandingPage />) },
  {
    path: "/login",
    element: withSuspense(
      <GuestRoute>
        <LoginPage />
      </GuestRoute>,
    ),
  },
  {
    path: "/register",
    element: withSuspense(
      <GuestRoute>
        <RegisterPage />
      </GuestRoute>,
    ),
  },
  {
    path: "/app",
    element: withSuspense(
      <ProtectedRoute>
        <WorkspacePage />
      </ProtectedRoute>,
    ),
  },
  { path: "/s/:token", element: withSuspense(<ShareAccessPage />) },
  {
    path: "/expired",
    element: withSuspense(<StatusPage kind="expired" />),
  },
  {
    path: "/unauthorized",
    element: withSuspense(<StatusPage kind="unauthorized" />),
  },
  {
    path: "/not-found",
    element: withSuspense(<StatusPage kind="not-found" />),
  },
  {
    path: "/deleted",
    element: withSuspense(<StatusPage kind="deleted" />),
  },
]);
