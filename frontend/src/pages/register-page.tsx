import { Link } from "react-router-dom";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { RegisterCard } from "@/features/auth/components/auth-shell";

export function RegisterPage() {
  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <Card className="rounded-[2rem] border-border/70">
          <CardHeader>
            <CardTitle>Register page</CardTitle>
            <CardDescription>
              The form stays aligned with the spec: email, username, nickname,
              and password.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm leading-6 text-muted-foreground">
            If you already have an account, go straight to the{" "}
            <Link className="underline underline-offset-4" to="/login">
              login page
            </Link>
            .
          </CardContent>
        </Card>
        <RegisterCard />
      </div>
    </div>
  );
}
