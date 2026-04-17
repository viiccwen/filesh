import { SparklesIcon, LogOutIcon } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { getInitials } from "@/lib/format";

import type { WorkspaceNavbarProps } from "./workspace-screen.types";

export function WorkspaceNavbar({ onLogout, user }: WorkspaceNavbarProps) {
  return (
    <header className="sticky top-4 z-40">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 rounded-full border border-border/70 bg-background/78 px-3 py-3 shadow-lg shadow-black/5 ring-1 ring-white/55 backdrop-blur-xl sm:px-5">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-full bg-foreground text-background">
            <SparklesIcon />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold tracking-[0.22em] text-foreground uppercase">
              filesh
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Avatar className="size-10 border border-border/70 bg-card">
            <AvatarFallback>{getInitials(user.nickname)}</AvatarFallback>
          </Avatar>
          <div className="hidden min-w-0 sm:block">
            <p className="truncate text-sm font-medium text-foreground">
              {user.nickname}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              @{user.username}
            </p>
          </div>
          <Button
            className="rounded-full"
            onClick={() => void onLogout()}
            size="icon"
            variant="outline"
          >
            <LogOutIcon data-icon="inline-start" />
            <span className="sr-only">Log out</span>
          </Button>
        </div>
      </div>
    </header>
  );
}
