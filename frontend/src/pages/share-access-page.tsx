import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function ShareAccessPage() {
  return (
    <Card className="mx-auto max-w-3xl rounded-[2rem] border-border/70">
      <CardHeader>
        <CardTitle>File access page</CardTitle>
        <CardDescription>
          This route is in place. The next step is wiring the real `/s/:token`
          share access flow and hiding owner-only actions according to
          permission.
        </CardDescription>
      </CardHeader>
      <CardContent className="text-sm leading-6 text-muted-foreground">
        Folder and file share access UI, expired or deleted semantic mapping,
        and share-policy-limited actions are still pending.
      </CardContent>
    </Card>
  );
}
