import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";

import { router } from "@/app/router";
import { Toaster } from "@/components/ui/sonner";
import { useAuthStore } from "@/features/auth/store";

export default function App() {
  const bootstrap = useAuthStore((state) => state.bootstrap);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  return (
    <>
      <RouterProvider router={router} />
      <Toaster richColors />
    </>
  );
}
