import { Link } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const productSignals = [
  "Feature-based frontend structure",
  "Zustand auth session state",
  "Zod form and API response validation",
  "Shadcn/ui powered workspace shell",
];

export function LandingPage() {
  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <Card className="rounded-[2rem] border-border/70">
        <CardHeader>
          <Badge variant="outline">Landing page</Badge>
          <CardTitle className="text-4xl leading-none sm:text-5xl">
            filesh is moving from a backend-first scaffold toward a spec-driven
            product.
          </CardTitle>
          <CardDescription className="max-w-2xl text-base leading-7">
            This pass pulls the frontend back toward the spec by splitting it
            into dedicated landing, login, register, file management, and status
            pages.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button asChild>
            <Link to="/login">Login</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/register">Register</Link>
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-[2rem] border-border/70">
        <CardHeader>
          <CardTitle>Current frontend direction</CardTitle>
          <CardDescription>
            These are the foundations aligned in this round.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          {productSignals.map((signal) => (
            <div
              key={signal}
              className="rounded-2xl border bg-muted/40 px-4 py-3 text-sm leading-6"
            >
              {signal}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
