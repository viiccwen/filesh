import { useEffect, useState } from "react";
import {
  ArrowDownToLineIcon,
  ArrowLeftIcon,
  FolderIcon,
  FolderPlusIcon,
  LinkIcon,
  Loader2Icon,
  LogOutIcon,
  ShieldCheckIcon,
  UploadIcon,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { type User } from "@/features/auth/schemas";
import { useAuthStore } from "@/features/auth/store";
import {
  ApiError,
  createFolder,
  createGuestFolderShare,
  downloadFile,
  getFolderContents,
  getFolderShare,
  getRootFolder,
  revokeFolderShare,
  uploadFile,
} from "@/lib/api";
import { formatBytes, formatDate, getInitials } from "@/lib/format";
import { type FolderContents, type Share } from "@/features/workspace/schemas";

export function WorkspaceScreen() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const [rootFolderId, setRootFolderId] = useState<string | null>(null);
  const [contents, setContents] = useState<FolderContents | null>(null);
  const [share, setShare] = useState<Share | null>(null);
  const [workspacePending, setWorkspacePending] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [folderPending, setFolderPending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sharePending, setSharePending] = useState(false);

  useEffect(() => {
    if (!accessToken) {
      return;
    }

    void loadWorkspace(accessToken);
  }, [accessToken]);

  if (!accessToken || !user) {
    return null;
  }

  async function loadWorkspace(token: string, folderId?: string) {
    setWorkspacePending(true);
    setWorkspaceError(null);

    try {
      const root = rootFolderId
        ? { id: rootFolderId }
        : await getRootFolder(token);
      const nextRootId = root.id;
      const targetFolderId = folderId ?? nextRootId;
      const nextContents = await getFolderContents(targetFolderId, token);
      const nextShare = await getFolderShare(token, targetFolderId);

      setRootFolderId(nextRootId);
      setContents(nextContents);
      setShare(nextShare);
    } catch (error) {
      setWorkspaceError(getErrorMessage(error));
    } finally {
      setWorkspacePending(false);
    }
  }

  async function handleCreateFolder(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!contents || !accessToken) return;
    setFolderPending(true);
    try {
      await createFolder(accessToken, {
        name: newFolderName,
        parent_id: contents.folder.id,
      });
      setNewFolderName("");
      await loadWorkspace(accessToken, contents.folder.id);
      toast.success("Folder created");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setFolderPending(false);
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !contents || !accessToken) return;
    setUploading(true);
    try {
      await uploadFile(accessToken, contents.folder.id, file);
      await loadWorkspace(accessToken, contents.folder.id);
      toast.success(`${file.name} uploaded`);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleDownload(fileId: string, filename: string) {
    if (!accessToken) return;

    try {
      const blob = await downloadFile(accessToken, fileId);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function handleCreateShare() {
    if (!contents || !accessToken) return;
    setSharePending(true);
    try {
      const nextShare = await createGuestFolderShare(
        accessToken,
        contents.folder.id,
      );
      setShare(nextShare);
      await navigator.clipboard.writeText(toAbsoluteUrl(nextShare.share_url));
      toast.success("Share link created and copied");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSharePending(false);
    }
  }

  async function handleRevokeShare() {
    if (!contents || !share || !accessToken) return;
    setSharePending(true);
    try {
      await revokeFolderShare(accessToken, contents.folder.id);
      setShare(null);
      toast.success("Share link revoked");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSharePending(false);
    }
  }

  const folderCount = contents?.folders.length ?? 0;
  const fileCount = contents?.files.length ?? 0;

  return (
    <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
      <aside className="flex flex-col gap-6">
        <Card className="rounded-[2rem] border-border/70">
          <CardHeader className="gap-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <Avatar className="size-12">
                  <AvatarFallback>{getInitials(user.nickname)}</AvatarFallback>
                </Avatar>
                <div>
                  <CardTitle className="text-xl">{user.nickname}</CardTitle>
                  <CardDescription>@{user.username}</CardDescription>
                </div>
              </div>
              <Button
                onClick={() => void logout()}
                size="icon-sm"
                variant="outline"
              >
                <LogOutIcon />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="grid gap-4">
            <MetricCard
              description="Subfolders in the current directory"
              label={`${folderCount}`}
              title="Folders"
            />
            <MetricCard
              description="Files in the current directory"
              label={`${fileCount}`}
              title="Files"
            />
          </CardContent>
          <CardFooter>
            <p className="text-sm text-muted-foreground">
              Created {formatDate(user.created_at)}
            </p>
          </CardFooter>
        </Card>

        <Card className="rounded-[2rem] border-border/70">
          <CardHeader>
            <CardTitle>Share status</CardTitle>
            <CardDescription>
              This stays as a side panel for now. The next iteration should
              promote it to the drawer or modal required by the spec.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {share ? (
              <>
                <div className="flex flex-wrap gap-2">
                  <Badge>Guest</Badge>
                  <Badge variant="outline">{share.permission_level}</Badge>
                </div>
                <div className="rounded-2xl border bg-muted/40 px-4 py-3 text-sm break-all">
                  {toAbsoluteUrl(share.share_url)}
                </div>
              </>
            ) : (
              <Empty className="border bg-muted/20 p-6">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <LinkIcon />
                  </EmptyMedia>
                  <EmptyTitle>No share yet</EmptyTitle>
                  <EmptyDescription>
                    This first pass only wires up guest share creation and
                    revoke.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </CardContent>
          <CardFooter className="flex flex-wrap gap-3">
            <Button
              disabled={sharePending}
              onClick={() => void handleCreateShare()}
            >
              {sharePending ? (
                <Loader2Icon
                  className="animate-spin"
                  data-icon="inline-start"
                />
              ) : (
                <LinkIcon data-icon="inline-start" />
              )}
              Create link
            </Button>
            <Button
              disabled={!share}
              onClick={() =>
                share &&
                navigator.clipboard.writeText(toAbsoluteUrl(share.share_url))
              }
              variant="outline"
            >
              Copy
            </Button>
            <Button
              disabled={!share || sharePending}
              onClick={() => void handleRevokeShare()}
              variant="ghost"
            >
              Revoke
            </Button>
          </CardFooter>
        </Card>
      </aside>

      <main className="flex flex-col gap-6">
        <Card className="rounded-[2rem] border-border/70">
          <CardHeader>
            <CardTitle>File management page</CardTitle>
            <CardDescription>
              {contents?.folder.path_cache ?? "/"}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-6">
            {workspaceError ? (
              <Alert variant="destructive">
                <AlertTitle>Workspace load failed</AlertTitle>
                <AlertDescription>{workspaceError}</AlertDescription>
              </Alert>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button
                disabled={!rootFolderId}
                onClick={() =>
                  void loadWorkspace(accessToken, rootFolderId ?? undefined)
                }
                variant="outline"
              >
                Root
              </Button>
              <Button
                disabled={!contents?.folder.parent_id}
                onClick={() =>
                  contents?.folder.parent_id &&
                  void loadWorkspace(accessToken, contents.folder.parent_id)
                }
                variant="outline"
              >
                <ArrowLeftIcon data-icon="inline-start" />
                Up one level
              </Button>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="border-border/70 shadow-none">
                <CardHeader>
                  <CardTitle className="text-lg">Create folder</CardTitle>
                </CardHeader>
                <CardContent>
                  <form
                    className="flex flex-col gap-4"
                    onSubmit={handleCreateFolder}
                  >
                    <FieldGroup>
                      <Field>
                        <FieldLabel htmlFor="new-folder-name">
                          Folder name
                        </FieldLabel>
                        <FieldContent>
                          <Input
                            id="new-folder-name"
                            value={newFolderName}
                            onChange={(event) =>
                              setNewFolderName(event.target.value)
                            }
                            required
                          />
                          <FieldDescription>
                            Backend validation still owns name collisions and
                            permission checks.
                          </FieldDescription>
                        </FieldContent>
                      </Field>
                    </FieldGroup>
                    <Button
                      disabled={folderPending || !newFolderName.trim()}
                      type="submit"
                    >
                      {folderPending ? (
                        <Loader2Icon
                          className="animate-spin"
                          data-icon="inline-start"
                        />
                      ) : (
                        <FolderPlusIcon data-icon="inline-start" />
                      )}
                      Create folder
                    </Button>
                  </form>
                </CardContent>
              </Card>

              <Card className="border-border/70 shadow-none">
                <CardHeader>
                  <CardTitle className="text-lg">Upload file</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-4">
                  <FieldGroup>
                    <Field>
                      <FieldLabel htmlFor="upload-file">
                        Choose a file
                      </FieldLabel>
                      <FieldContent>
                        <Input
                          id="upload-file"
                          disabled={uploading}
                          onChange={(event) => void handleUpload(event)}
                          type="file"
                        />
                        <FieldDescription>
                          Uploads follow the init, content, and finalize
                          sequence.
                        </FieldDescription>
                      </FieldContent>
                    </Field>
                  </FieldGroup>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    {uploading ? (
                      <Loader2Icon className="animate-spin" />
                    ) : (
                      <UploadIcon />
                    )}
                    {uploading
                      ? "Uploading now"
                      : "The current directory refreshes after upload completes"}
                  </div>
                </CardContent>
              </Card>
            </div>

            <Separator />

            {workspacePending && !contents ? (
              <div className="flex flex-col gap-3">
                <Skeleton className="h-12 rounded-2xl" />
                <Skeleton className="h-12 rounded-2xl" />
                <Skeleton className="h-12 rounded-2xl" />
              </div>
            ) : contents && folderCount + fileCount > 0 ? (
              <div className="overflow-hidden rounded-2xl border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Updated</TableHead>
                      <TableHead>Size</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {contents.folders.map((folder) => (
                      <TableRow key={folder.id}>
                        <TableCell className="font-medium">
                          {folder.name}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">Folder</Badge>
                        </TableCell>
                        <TableCell>{formatDate(folder.updated_at)}</TableCell>
                        <TableCell>-</TableCell>
                        <TableCell className="text-right">
                          <Button
                            onClick={() =>
                              void loadWorkspace(accessToken, folder.id)
                            }
                            size="sm"
                            variant="outline"
                          >
                            <FolderIcon data-icon="inline-start" />
                            Open
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                    {contents.files.map((file) => (
                      <TableRow key={file.id}>
                        <TableCell className="font-medium">
                          {file.stored_filename}
                        </TableCell>
                        <TableCell>
                          <Badge>{file.status}</Badge>
                        </TableCell>
                        <TableCell>-</TableCell>
                        <TableCell>{formatBytes(file.size_bytes)}</TableCell>
                        <TableCell className="text-right">
                          <Button
                            onClick={() =>
                              void handleDownload(file.id, file.stored_filename)
                            }
                            size="sm"
                            variant="outline"
                          >
                            <ArrowDownToLineIcon data-icon="inline-start" />
                            Download
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <Empty className="border bg-muted/20">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <ShieldCheckIcon />
                  </EmptyMedia>
                  <EmptyTitle>This folder is empty</EmptyTitle>
                  <EmptyDescription>
                    Folder tree, search, sort, and pagination are still missing
                    and should be added next.
                  </EmptyDescription>
                </EmptyHeader>
                <EmptyContent />
              </Empty>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}

function MetricCard({
  description,
  label,
  title,
}: {
  description: string;
  label: string;
  title: string;
}) {
  return (
    <div className="rounded-[1.5rem] border bg-background/70 p-4">
      <p className="text-sm text-muted-foreground">{title}</p>
      <p className="mt-2 text-2xl font-semibold">{label}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        {description}
      </p>
    </div>
  );
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Unexpected error";
}

function toAbsoluteUrl(pathname: string): string {
  return new URL(pathname, window.location.origin).toString();
}
