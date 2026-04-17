import { Link } from "react-router-dom";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LoginCard } from "@/features/auth/components/auth-shell";

export function LoginPage() {
  return (
    <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
      <Card className="rounded-[2rem] border-border/70">
        <CardHeader>
          <CardTitle>Login page</CardTitle>
          <CardDescription>
            This matches the spec as a dedicated login page instead of a tab
            embedded in the landing page.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm leading-6 text-muted-foreground">
          If you do not have an account yet, head to the{" "}
          <Link className="underline underline-offset-4" to="/register">
            register page
          </Link>
          .
        </CardContent>
      </Card>
      <LoginCard />
    </div>
  );
}
