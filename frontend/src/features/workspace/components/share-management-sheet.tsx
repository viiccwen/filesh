import { useEffect, useState } from "react";
import { Link2Icon, Loader2Icon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  shareFormSchema,
  type Share,
  type ShareFormValues,
} from "@/features/workspace/schemas";

const defaultValues: ShareFormValues = {
  share_mode: "GUEST",
  permission_level: "VIEW_DOWNLOAD",
  expiry: "never",
  invitation_emails: [],
};

type ShareManagementSheetProps = {
  onCopyLink: () => Promise<void>;
  onSave: (values: ShareFormValues) => Promise<void>;
  onRevoke: () => Promise<void>;
  open: boolean;
  pending: boolean;
  setOpen: (open: boolean) => void;
  share: Share | null;
};

export function ShareManagementSheet({
  onCopyLink,
  onRevoke,
  onSave,
  open,
  pending,
  setOpen,
  share,
}: ShareManagementSheetProps) {
  const [error, setError] = useState<string | null>(null);
  const [emailList, setEmailList] = useState("");
  const [values, setValues] = useState<ShareFormValues>(defaultValues);

  useEffect(() => {
    if (!share) {
      setValues(defaultValues);
      setEmailList("");
      setError(null);
      return;
    }

    setValues({
      share_mode: share.share_mode,
      permission_level: share.permission_level,
      expiry: share.expires_at ? "day" : "never",
      invitation_emails: share.invitation_emails,
    });
    setEmailList(share.invitation_emails.join(", "));
    setError(null);
  }, [share]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const invitation_emails = emailList
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    const parsed = shareFormSchema.safeParse({
      ...values,
      invitation_emails,
    });

    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "Invalid share settings");
      return;
    }

    setError(null);
    await onSave(parsed.data);
  }

  return (
    <Sheet onOpenChange={setOpen} open={open}>
      <SheetContent className="w-full sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>Share management</SheetTitle>
          <SheetDescription>
            Create or update the active share link for the current folder.
          </SheetDescription>
        </SheetHeader>

        <form
          className="flex flex-1 flex-col gap-6 overflow-y-auto px-4 pb-4"
          onSubmit={handleSubmit}
        >
          <div className="flex flex-wrap gap-2">
            <Badge variant={share ? "default" : "secondary"}>
              {share ? "Active share" : "No active share"}
            </Badge>
            {share ? (
              <Badge variant="outline">{share.permission_level}</Badge>
            ) : null}
          </div>

          {error ? (
            <Alert variant="destructive">
              <AlertTitle>Share settings failed validation</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          <FieldGroup>
            <Field>
              <FieldLabel>Share mode</FieldLabel>
              <FieldContent>
                <Select
                  onValueChange={(value) =>
                    setValues((current) => ({
                      ...current,
                      share_mode: value as ShareFormValues["share_mode"],
                    }))
                  }
                  value={values.share_mode}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a mode" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="GUEST">Guest</SelectItem>
                      <SelectItem value="USER_ONLY">User only</SelectItem>
                      <SelectItem value="EMAIL_INVITATION">
                        Email invitation
                      </SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
                <FieldDescription>
                  The backend still owns access control. This form only edits
                  share policy inputs.
                </FieldDescription>
              </FieldContent>
            </Field>

            <Field>
              <FieldLabel>Permission level</FieldLabel>
              <FieldContent>
                <Select
                  onValueChange={(value) =>
                    setValues((current) => ({
                      ...current,
                      permission_level:
                        value as ShareFormValues["permission_level"],
                    }))
                  }
                  value={values.permission_level}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a permission" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="VIEW_DOWNLOAD">
                        View and download
                      </SelectItem>
                      <SelectItem value="UPLOAD">Upload</SelectItem>
                      <SelectItem value="DELETE">Delete</SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </FieldContent>
            </Field>

            <Field>
              <FieldLabel>Expiry</FieldLabel>
              <FieldContent>
                <Select
                  onValueChange={(value) =>
                    setValues((current) => ({
                      ...current,
                      expiry: value as ShareFormValues["expiry"],
                    }))
                  }
                  value={values.expiry}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select an expiry" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="hour">1 hour</SelectItem>
                      <SelectItem value="day">1 day</SelectItem>
                      <SelectItem value="never">Never</SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </FieldContent>
            </Field>

            <Field data-disabled={values.share_mode !== "EMAIL_INVITATION"}>
              <FieldLabel htmlFor="share-invitations">
                Invitation emails
              </FieldLabel>
              <FieldContent>
                <Input
                  disabled={values.share_mode !== "EMAIL_INVITATION"}
                  id="share-invitations"
                  onChange={(event) => setEmailList(event.target.value)}
                  placeholder="alice@example.com, bob@example.com"
                  value={emailList}
                />
                <FieldDescription>
                  Use comma-separated email addresses when the mode is Email
                  invitation.
                </FieldDescription>
              </FieldContent>
            </Field>

            {share ? (
              <Field>
                <FieldLabel htmlFor="share-link">Active link</FieldLabel>
                <FieldContent>
                  <Input id="share-link" readOnly value={share.share_url} />
                </FieldContent>
              </Field>
            ) : null}
          </FieldGroup>

          <SheetFooter className="px-0 pb-0">
            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
              <Button disabled={pending} type="submit">
                {pending ? (
                  <Loader2Icon
                    className="animate-spin"
                    data-icon="inline-start"
                  />
                ) : (
                  <Link2Icon data-icon="inline-start" />
                )}
                {share ? "Update share" : "Create share"}
              </Button>
              <Button
                disabled={!share || pending}
                onClick={() => void onCopyLink()}
                type="button"
                variant="outline"
              >
                Copy link
              </Button>
              <Button
                disabled={!share || pending}
                onClick={() => void onRevoke()}
                type="button"
                variant="ghost"
              >
                Revoke
              </Button>
            </div>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
  );
}
