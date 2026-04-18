import { LogOutIcon } from "lucide-react";

import { AppNavbar, AppNavbarUser } from "@/components/app-navbar";
import { Button } from "@/components/ui/button";

import type { WorkspaceNavbarProps } from "./workspace-screen.types";

export function WorkspaceNavbar({ onLogout, user }: WorkspaceNavbarProps) {
  return (
    <AppNavbar innerClassName="max-w-7xl">
      <AppNavbarUser nickname={user.nickname} username={user.username} />
      <Button
        className="rounded-full"
        onClick={() => void onLogout()}
        size="icon"
        variant="outline"
      >
        <LogOutIcon data-icon="inline-start" />
        <span className="sr-only">Log out</span>
      </Button>
    </AppNavbar>
  );
}
