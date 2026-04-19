import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { SparklesIcon } from "lucide-react";

import brandMark from "@/components/image.png";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { getInitials } from "@/lib/format";
import { cn } from "@/lib/utils";

type AppNavbarProps = {
  brandHref?: string;
  children?: ReactNode;
  className?: string;
  innerClassName?: string;
};

type AppNavbarUserProps = {
  fallback?: string;
  nickname?: string | null;
  username?: string | null;
};

export function AppNavbar({
  brandHref = "/",
  children,
  className,
  innerClassName,
}: AppNavbarProps) {
  return (
    <header className={cn("sticky top-4 z-40", className)}>
      <div
        className={cn(
          "mx-auto flex items-center justify-between gap-3 rounded-full border border-border/70 bg-background/78 px-3 py-3 shadow-lg shadow-black/5 ring-1 ring-white/55 backdrop-blur-xl sm:px-5",
          innerClassName,
        )}
      >
        <Link className="flex items-center gap-3" to={brandHref}>
          <img alt="filesh logo" height={25} src={brandMark} width={25} />
          <div className="min-w-0">
            <p className="text-sm font-semibold tracking-[0.22em] text-foreground uppercase">
              filesh
            </p>
          </div>
        </Link>

        {children ? (
          <div className="flex items-center gap-2 sm:gap-3">{children}</div>
        ) : null}
      </div>
    </header>
  );
}

export function AppNavbarUser({
  fallback = "FS",
  nickname,
  username,
}: AppNavbarUserProps) {
  return (
    <>
      <Avatar className="size-10 border border-border/70 bg-card">
        <AvatarFallback>
          {nickname ? getInitials(nickname) : fallback}
        </AvatarFallback>
      </Avatar>
      {nickname && username ? (
        <div className="hidden min-w-0 sm:block">
          <p className="truncate text-sm font-medium text-foreground">
            {nickname}
          </p>
          <p className="truncate text-xs text-muted-foreground">@{username}</p>
        </div>
      ) : null}
    </>
  );
}
