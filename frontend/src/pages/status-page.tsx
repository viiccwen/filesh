import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const statusCopy = {
  deleted: {
    title: "Deleted page",
    description:
      "This resource has been deleted, and the old share link is no longer valid.",
  },
  expired: {
    title: "Expired page",
    description: "This share link has expired.",
  },
  "not-found": {
    title: "Resource not found page",
    description: "The requested resource or share link could not be found.",
  },
  unauthorized: {
    title: "Unauthorized page",
    description:
      "You do not currently have permission to access this resource.",
  },
} as const;

export function StatusPage({ kind }: { kind: keyof typeof statusCopy }) {
  const copy = statusCopy[kind];

  return (
    <Card className="mx-auto max-w-2xl rounded-[2rem] border-border/70">
      <CardHeader>
        <CardTitle>{copy.title}</CardTitle>
        <CardDescription>{copy.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Button asChild>
          <Link to="/">Return home</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
