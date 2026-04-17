import { createBrowserRouter, Navigate } from "react-router-dom";

import { useAuthStore } from "@/features/auth/store";
import { LandingPage } from "@/pages/landing-page";
import { LoginPage } from "@/pages/login-page";
import { RegisterPage } from "@/pages/register-page";
import { ShareAccessPage } from "@/pages/share-access-page";
import { StatusPage } from "@/pages/status-page";
import { WorkspacePage } from "@/pages/workspace-page";

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

export const router = createBrowserRouter([
  { path: "/", element: <LandingPage /> },
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    path: "/app",
    element: (
      <ProtectedRoute>
        <WorkspacePage />
      </ProtectedRoute>
    ),
  },
  { path: "/s/:token", element: <ShareAccessPage /> },
  { path: "/expired", element: <StatusPage kind="expired" /> },
  { path: "/unauthorized", element: <StatusPage kind="unauthorized" /> },
  { path: "/not-found", element: <StatusPage kind="not-found" /> },
  { path: "/deleted", element: <StatusPage kind="deleted" /> },
]);
