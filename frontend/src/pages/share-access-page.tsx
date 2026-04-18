import {
  ArrowDownToLineIcon,
  FileTextIcon,
  FolderIcon,
  Link2Icon,
  Loader2Icon,
  LogOutIcon,
} from "lucide-react";
import { Fragment, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { AppNavbar, AppNavbarUser } from "@/components/app-navbar";
import {
  ApiError,
  downloadSharedFile,
  downloadSharedFolderFile,
  getShareAccess,
  getSharedFolderContents,
} from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import { useAuthStore } from "@/features/auth/store";
import type {
  FileSummary,
  Folder,
  ShareAccessResponse,
  SharedFolderContentsResponse,
} from "@/features/workspace/schemas";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type ShareListItem =
  | { kind: "folder"; folder: Folder }
  | { kind: "file"; file: FileSummary };

export function ShareAccessPage() {
  const { token = "" } = useParams();
  const navigate = useNavigate();

  const accessToken = useAuthStore((state) => state.accessToken);
  const status = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const [shareAccess, setShareAccess] = useState<ShareAccessResponse | null>(
    null,
  );
  const [folderContents, setFolderContents] =
    useState<SharedFolderContentsResponse | null>(null);
  const [knownFolders, setKnownFolders] = useState<Record<string, Folder>>({});
  const [pending, setPending] = useState(true);
  const [downloadPending, setDownloadPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      navigate("/not-found", { replace: true });
      return;
    }

    void bootstrapShareAccess();
  }, [accessToken, navigate, token]);

  const breadcrumbFolders = useMemo(() => {
    if (!folderContents) {
      return [];
    }

    const chain: Folder[] = [];
    let currentFolder: Folder | undefined = folderContents.folder;

    while (currentFolder) {
      chain.unshift(currentFolder);
      currentFolder = currentFolder.parent_id
        ? knownFolders[currentFolder.parent_id]
        : undefined;
    }

    return chain;
  }, [folderContents, knownFolders]);

  const items = useMemo<ShareListItem[]>(() => {
    if (!folderContents) {
      return [];
    }

    return [
      ...folderContents.folders
        .slice()
        .sort((left, right) => left.name.localeCompare(right.name))
        .map((folder) => ({ kind: "folder", folder }) as const),
      ...folderContents.files
        .slice()
        .sort((left, right) =>
          left.stored_filename.localeCompare(right.stored_filename),
        )
        .map((file) => ({ kind: "file", file }) as const),
    ];
  }, [folderContents]);

  const permissionLevel =
    folderContents?.permission_level ?? shareAccess?.permission_level ?? null;

  if (pending) {
    return (
      <div className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 pb-10 pt-2">
          <Skeleton className="h-16 rounded-full" />
          <Skeleton className="h-40 rounded-[2rem]" />
          <Skeleton className="h-[24rem] rounded-[2rem]" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 pb-10 pt-2">
        <AppNavbar innerClassName="max-w-7xl">
          <Badge variant="outline">Shared access</Badge>
          {status === "authenticated" && user ? (
            <>
              <AppNavbarUser
                nickname={user.nickname}
                username={user.username}
              />
              <Button
                className="rounded-full"
                onClick={() => void logout()}
                size="icon"
                variant="outline"
              >
                <LogOutIcon data-icon="inline-start" />
                <span className="sr-only">Log out</span>
              </Button>
            </>
          ) : (
            <Button asChild className="rounded-full" variant="outline">
              <Link to="/login">Login</Link>
            </Button>
          )}
        </AppNavbar>

        {error ? (
          <Alert variant="destructive">
            <AlertTitle>Shared access failed</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {shareAccess?.resource_type === "FILE" && shareAccess.file ? (
          <main className="relative overflow-hidden rounded-[2.5rem] border border-border/70 bg-background/78 px-6 py-12 shadow-lg shadow-black/5 ring-1 ring-white/40 backdrop-blur-xl sm:px-10">
            <div className="absolute inset-x-0 top-0 h-40 bg-linear-to-br from-primary/10 via-transparent to-chart-2/12" />
            <div className="absolute right-0 top-10 size-64 rounded-full bg-primary/10 blur-3xl" />

            <div className="relative mx-auto flex max-w-3xl flex-col items-center gap-6 text-center">
              <div className="flex size-18 items-center justify-center rounded-full bg-primary/10 text-primary">
                <FileTextIcon />
              </div>
              <div>
                <h1 className="text-4xl tracking-[-0.05em] text-foreground sm:text-5xl">
                  {shareAccess.file.stored_filename}
                </h1>
                <p className="mt-4 text-sm leading-7 text-muted-foreground sm:text-base">
                  Direct file access from filesh. Download the file with the
                  active share policy applied.
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <Badge variant="outline">{shareAccess.share_mode}</Badge>
                <Badge>{shareAccess.permission_level}</Badge>
                {shareAccess.expires_at ? (
                  <Badge variant="secondary">
                    Expires {formatDate(shareAccess.expires_at)}
                  </Badge>
                ) : null}
              </div>
              <div className="grid w-full gap-3 rounded-[1.5rem] border border-border/60 bg-background/60 p-5 text-left sm:grid-cols-3">
                <InfoBlock label="Status" value={shareAccess.file.status} />
                <InfoBlock
                  label="Size"
                  value={formatBytes(shareAccess.file.size_bytes)}
                />
                <InfoBlock
                  label="Updated"
                  value={formatDate(shareAccess.file.updated_at)}
                />
              </div>
              <Button
                className="rounded-full px-6"
                disabled={downloadPending}
                onClick={() => void handleDownloadRootFile()}
              >
                {downloadPending ? (
                  <Loader2Icon
                    className="animate-spin"
                    data-icon="inline-start"
                  />
                ) : (
                  <ArrowDownToLineIcon data-icon="inline-start" />
                )}
                Download file
              </Button>
            </div>
          </main>
        ) : (
          <main className="flex min-w-0 flex-col gap-6">
            <section className="flex flex-col gap-5">
              <div className="flex min-w-0 flex-col gap-3">
                <Breadcrumb>
                  <BreadcrumbList>
                    {breadcrumbFolders.length > 0 ? (
                      breadcrumbFolders.map((folder, index) => {
                        const isLast = index === breadcrumbFolders.length - 1;

                        return (
                          <Fragment key={folder.id}>
                            <BreadcrumbItem>
                              {isLast ? (
                                <BreadcrumbPage>{folder.name}</BreadcrumbPage>
                              ) : (
                                <BreadcrumbLink
                                  className="cursor-pointer"
                                  onClick={() =>
                                    void openSharedFolder(folder.id)
                                  }
                                >
                                  {folder.name}
                                </BreadcrumbLink>
                              )}
                            </BreadcrumbItem>
                            {!isLast ? <BreadcrumbSeparator /> : null}
                          </Fragment>
                        );
                      })
                    ) : (
                      <BreadcrumbItem>
                        <BreadcrumbPage>Shared workspace</BreadcrumbPage>
                      </BreadcrumbItem>
                    )}
                  </BreadcrumbList>
                </Breadcrumb>

                <div className="flex flex-wrap items-end justify-between gap-4">
                  <div>
                    <h1 className="text-4xl tracking-[-0.05em] text-foreground sm:text-5xl">
                      Shared workspace
                    </h1>
                    <p className="mt-2 max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">
                      Open folders or download files directly from this shared
                      workspace view.
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {shareAccess ? (
                      <Badge variant="outline">{shareAccess.share_mode}</Badge>
                    ) : null}
                    {permissionLevel ? <Badge>{permissionLevel}</Badge> : null}
                    {shareAccess?.expires_at ? (
                      <Badge variant="secondary">
                        Expires {formatDate(shareAccess.expires_at)}
                      </Badge>
                    ) : null}
                  </div>
                </div>
              </div>
            </section>

            {items.length === 0 ? (
              <Empty className="border bg-muted/20 py-16">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <Link2Icon />
                  </EmptyMedia>
                  <EmptyTitle>This shared folder is empty</EmptyTitle>
                  <EmptyDescription>
                    The current share is active, but there are no folders or
                    files in this location yet.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : (
              <div className="overflow-hidden rounded-[1.75rem] border border-border/70 bg-background/70 shadow-lg shadow-black/5 backdrop-blur">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Kind</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Updated</TableHead>
                      <TableHead>Size</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.map((item) => (
                      <TableRow
                        className="cursor-pointer transition-colors hover:bg-muted/20"
                        key={
                          item.kind === "folder" ? item.folder.id : item.file.id
                        }
                        onClick={() =>
                          item.kind === "folder"
                            ? void openSharedFolder(item.folder.id)
                            : void handleDownloadFolderFile(
                                item.file.id,
                                item.file.stored_filename,
                              )
                        }
                      >
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-3">
                            {item.kind === "folder" ? (
                              <FolderIcon className="text-muted-foreground" />
                            ) : (
                              <FileTextIcon className="text-muted-foreground" />
                            )}
                            <span>
                              {item.kind === "folder"
                                ? item.folder.name
                                : item.file.stored_filename}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {item.kind === "folder" ? "Folder" : "File"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {item.kind === "folder" ? (
                            <span className="text-muted-foreground">—</span>
                          ) : (
                            <Badge>{item.file.status}</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {formatDate(
                            item.kind === "folder"
                              ? item.folder.updated_at
                              : item.file.updated_at,
                          )}
                        </TableCell>
                        <TableCell>
                          {item.kind === "folder"
                            ? "—"
                            : formatBytes(item.file.size_bytes)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </main>
        )}
      </div>
    </div>
  );

  async function bootstrapShareAccess() {
    setPending(true);
    setError(null);

    try {
      const nextAccess = await getShareAccess(token, accessToken);
      setShareAccess(nextAccess);

      if (nextAccess.resource_type === "FOLDER") {
        const nextContents = await getSharedFolderContents(token, accessToken);
        setFolderContents(nextContents);
        registerFolders(nextContents.folder, nextContents.folders);
      }
    } catch (error) {
      handleShareError(error);
    } finally {
      setPending(false);
    }
  }

  async function openSharedFolder(folderId: string) {
    try {
      const nextContents = await getSharedFolderContents(
        token,
        accessToken,
        folderId,
      );
      setFolderContents(nextContents);
      registerFolders(nextContents.folder, nextContents.folders);
    } catch (error) {
      handleShareError(error);
    }
  }

  async function handleDownloadRootFile() {
    if (!shareAccess?.file) {
      return;
    }

    setDownloadPending(true);
    try {
      const blob = await downloadSharedFile(token, accessToken);
      downloadBlob(blob, shareAccess.file.stored_filename);
    } catch (error) {
      handleShareError(error);
    } finally {
      setDownloadPending(false);
    }
  }

  async function handleDownloadFolderFile(fileId: string, filename: string) {
    try {
      const blob = await downloadSharedFolderFile(token, fileId, accessToken);
      downloadBlob(blob, filename);
    } catch (error) {
      handleShareError(error);
    }
  }

  function registerFolders(folder: Folder, childFolders: Folder[]) {
    setKnownFolders((current) => {
      const next = { ...current, [folder.id]: folder };

      for (const childFolder of childFolders) {
        next[childFolder.id] = childFolder;
      }

      return next;
    });
  }

  function handleShareError(error: unknown) {
    if (error instanceof ApiError) {
      if (
        error.status === 410 ||
        error.message.toLowerCase().includes("expired")
      ) {
        navigate("/expired", { replace: true });
        return;
      }

      if (
        error.status === 403 ||
        error.message.toLowerCase().includes("unauthorized")
      ) {
        navigate("/unauthorized", { replace: true });
        return;
      }

      if (
        error.status === 404 &&
        error.message.toLowerCase().includes("resource not found")
      ) {
        navigate("/deleted", { replace: true });
        return;
      }

      if (error.status === 404) {
        navigate("/not-found", { replace: true });
        return;
      }
    }

    setError(error instanceof Error ? error.message : "Unexpected error");
    toast.error(error instanceof Error ? error.message : "Unexpected error");
  }
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p className="text-sm font-medium text-foreground">{value}</p>
    </div>
  );
}
