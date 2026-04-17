import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownToLineIcon,
  ArrowLeftIcon,
  ChevronRightIcon,
  ChevronsLeftRightEllipsisIcon,
  FolderIcon,
  FolderPlusIcon,
  Link2Icon,
  Loader2Icon,
  LogOutIcon,
  SearchIcon,
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
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { useAuthStore } from "@/features/auth/store";
import { ShareManagementSheet } from "@/features/workspace/components/share-management-sheet";
import {
  shareFormSchema,
  type Folder,
  type FolderContents,
  type Share,
  type ShareFormValues,
} from "@/features/workspace/schemas";
import {
  ApiError,
  createFolder,
  createFolderShare,
  downloadFile,
  getFolderContents,
  getFolderShare,
  getRootFolder,
  revokeFolderShare,
  updateFolderShare,
  uploadFile,
} from "@/lib/api";
import { formatBytes, formatDate, getInitials } from "@/lib/format";

type WorkspaceItem = {
  id: string;
  kind: "file" | "folder";
  name: string;
  size: number | null;
  status: string;
  updatedAt: string;
};

type FolderNode = {
  folder: Folder;
  childFolderIds: string[];
};

type SortKey = "name" | "updatedAt" | "size" | "kind";

const PAGE_SIZE_OPTIONS = ["5", "10", "20"];

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
  const [shareSheetOpen, setShareSheetOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [pageSize, setPageSize] = useState(10);
  const [pageIndex, setPageIndex] = useState(1);
  const [folderTree, setFolderTree] = useState<Record<string, FolderNode>>({});
  const [expandedFolderIds, setExpandedFolderIds] = useState<Set<string>>(
    new Set(),
  );

  useEffect(() => {
    if (!accessToken) {
      return;
    }

    void loadWorkspace(accessToken);
  }, [accessToken]);

  useEffect(() => {
    setPageIndex(1);
  }, [searchQuery, sortDirection, sortKey, pageSize, contents?.folder.id]);

  const items = useMemo<WorkspaceItem[]>(() => {
    if (!contents) {
      return [];
    }

    return [
      ...contents.folders.map((folder) => ({
        id: folder.id,
        kind: "folder" as const,
        name: folder.name,
        size: null,
        status: "READY",
        updatedAt: folder.updated_at,
      })),
      ...contents.files.map((file) => ({
        id: file.id,
        kind: "file" as const,
        name: file.stored_filename,
        size: file.size_bytes,
        status: file.status,
        updatedAt: file.updated_at,
      })),
    ];
  }, [contents]);

  const filteredItems = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();

    return items.filter((item) =>
      normalizedQuery
        ? item.name.toLowerCase().includes(normalizedQuery)
        : true,
    );
  }, [items, searchQuery]);

  const sortedItems = useMemo(() => {
    const nextItems = [...filteredItems];
    const directionFactor = sortDirection === "asc" ? 1 : -1;

    nextItems.sort((left, right) => {
      switch (sortKey) {
        case "kind":
          return left.kind.localeCompare(right.kind) * directionFactor;
        case "size":
          return ((left.size ?? -1) - (right.size ?? -1)) * directionFactor;
        case "updatedAt":
          return (
            (new Date(left.updatedAt).getTime() -
              new Date(right.updatedAt).getTime()) *
            directionFactor
          );
        case "name":
        default:
          return (
            left.name.localeCompare(right.name, undefined, {
              sensitivity: "base",
            }) * directionFactor
          );
      }
    });

    return nextItems;
  }, [filteredItems, sortDirection, sortKey]);

  const totalPages = Math.max(1, Math.ceil(sortedItems.length / pageSize));
  const paginatedItems = useMemo(() => {
    const startIndex = (pageIndex - 1) * pageSize;
    return sortedItems.slice(startIndex, startIndex + pageSize);
  }, [pageIndex, pageSize, sortedItems]);

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
      registerFolderTreeNode(nextContents.folder, nextContents.folders);
      setExpandedFolderIds((current) =>
        new Set(current).add(nextContents.folder.id),
      );
    } catch (error) {
      setWorkspaceError(getErrorMessage(error));
    } finally {
      setWorkspacePending(false);
    }
  }

  function registerFolderTreeNode(folder: Folder, childFolders: Folder[]) {
    setFolderTree((current) => {
      const nextEntries = { ...current };
      nextEntries[folder.id] = {
        childFolderIds: childFolders.map((item) => item.id),
        folder,
      };

      for (const childFolder of childFolders) {
        const existing = current[childFolder.id];
        nextEntries[childFolder.id] = {
          childFolderIds: existing?.childFolderIds ?? [],
          folder: childFolder,
        };
      }

      return nextEntries;
    });
  }

  async function openFolder(folderId: string) {
    const token = accessToken;
    if (!token) {
      return;
    }

    await loadWorkspace(token, folderId);
  }

  async function toggleFolderExpansion(folderId: string) {
    const token = accessToken;
    if (!token) {
      return;
    }

    setExpandedFolderIds((current) => {
      const next = new Set(current);
      if (next.has(folderId)) {
        next.delete(folderId);
      } else {
        next.add(folderId);
      }
      return next;
    });

    if (!folderTree[folderId]?.childFolderIds.length) {
      try {
        const nextContents = await getFolderContents(folderId, token);
        registerFolderTreeNode(nextContents.folder, nextContents.folders);
      } catch (error) {
        toast.error(getErrorMessage(error));
      }
    }
  }

  async function handleCreateFolder(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = accessToken;
    if (!contents || !token) {
      return;
    }

    setFolderPending(true);
    try {
      await createFolder(token, {
        name: newFolderName,
        parent_id: contents.folder.id,
      });
      setNewFolderName("");
      await loadWorkspace(token, contents.folder.id);
      toast.success("Folder created");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setFolderPending(false);
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    const token = accessToken;
    if (!file || !contents || !token) {
      return;
    }

    setUploading(true);
    try {
      await uploadFile(token, contents.folder.id, file);
      await loadWorkspace(token, contents.folder.id);
      toast.success(`${file.name} uploaded`);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleDownload(fileId: string, filename: string) {
    const token = accessToken;
    if (!token) {
      return;
    }

    try {
      const blob = await downloadFile(token, fileId);
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

  async function handleSaveShare(values: ShareFormValues) {
    const token = accessToken;
    if (!contents || !token) {
      return;
    }

    const normalizedValues = shareFormSchema.parse(values);
    setSharePending(true);

    try {
      const nextShare = share
        ? await updateFolderShare(token, contents.folder.id, normalizedValues)
        : await createFolderShare(token, contents.folder.id, normalizedValues);

      setShare(nextShare);
      setShareSheetOpen(false);
      toast.success(share ? "Share updated" : "Share created");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSharePending(false);
    }
  }

  async function handleCopyShareLink() {
    if (!share) {
      return;
    }

    try {
      await navigator.clipboard.writeText(toAbsoluteUrl(share.share_url));
      toast.success("Share link copied");
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  }

  async function handleRevokeShare() {
    const token = accessToken;
    if (!contents || !share || !token) {
      return;
    }

    setSharePending(true);
    try {
      await revokeFolderShare(token, contents.folder.id);
      setShare(null);
      setShareSheetOpen(false);
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
    <>
      <ShareManagementSheet
        onCopyLink={handleCopyShareLink}
        onRevoke={handleRevokeShare}
        onSave={handleSaveShare}
        open={shareSheetOpen}
        pending={sharePending}
        setOpen={setShareSheetOpen}
        share={share}
      />

      <div className="grid gap-6 xl:grid-cols-[320px_1fr]">
        <aside className="flex flex-col gap-6">
          <Card className="rounded-[2rem] border-border/70">
            <CardHeader className="gap-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <Avatar className="size-12">
                    <AvatarFallback>
                      {getInitials(user.nickname)}
                    </AvatarFallback>
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
              <CardTitle>Folder tree</CardTitle>
              <CardDescription>
                This tree grows lazily from the folder contents that have
                already been loaded.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {rootFolderId ? (
                <FolderTree
                  activeFolderId={contents?.folder.id ?? null}
                  expandedFolderIds={expandedFolderIds}
                  nodes={folderTree}
                  onOpenFolder={openFolder}
                  onToggleFolder={toggleFolderExpansion}
                  rootFolderId={rootFolderId}
                />
              ) : (
                <div className="flex flex-col gap-2">
                  <Skeleton className="h-8 rounded-xl" />
                  <Skeleton className="h-8 rounded-xl" />
                </div>
              )}
            </CardContent>
          </Card>
        </aside>

        <main className="flex flex-col gap-6">
          <Card className="rounded-[2rem] border-border/70">
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>File management page</CardTitle>
                  <CardDescription>
                    {contents?.folder.path_cache ?? "/"}
                  </CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={() => setShareSheetOpen(true)}
                    variant={share ? "outline" : "default"}
                  >
                    <Link2Icon data-icon="inline-start" />
                    Manage share
                  </Button>
                  <Button
                    disabled={!contents?.folder.parent_id}
                    onClick={() =>
                      contents?.folder.parent_id
                        ? void openFolder(contents.folder.parent_id)
                        : undefined
                    }
                    variant="outline"
                  >
                    <ArrowLeftIcon data-icon="inline-start" />
                    Up one level
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent className="flex flex-col gap-6">
              {workspaceError ? (
                <Alert variant="destructive">
                  <AlertTitle>Workspace load failed</AlertTitle>
                  <AlertDescription>{workspaceError}</AlertDescription>
                </Alert>
              ) : null}

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
                              onChange={(event) =>
                                setNewFolderName(event.target.value)
                              }
                              value={newFolderName}
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
                            disabled={uploading}
                            id="upload-file"
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

              <div className="grid gap-4 xl:grid-cols-[1fr_auto_auto_auto]">
                <Field>
                  <FieldLabel htmlFor="workspace-search">Search</FieldLabel>
                  <FieldContent>
                    <div className="relative">
                      <SearchIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        className="pl-9"
                        id="workspace-search"
                        onChange={(event) => setSearchQuery(event.target.value)}
                        placeholder="Search folders and files in this directory"
                        value={searchQuery}
                      />
                    </div>
                  </FieldContent>
                </Field>

                <Field>
                  <FieldLabel>Sort by</FieldLabel>
                  <FieldContent>
                    <Select
                      onValueChange={(value) => setSortKey(value as SortKey)}
                      value={sortKey}
                    >
                      <SelectTrigger className="w-full sm:w-40">
                        <SelectValue placeholder="Sort field" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectItem value="name">Name</SelectItem>
                          <SelectItem value="updatedAt">Updated</SelectItem>
                          <SelectItem value="size">Size</SelectItem>
                          <SelectItem value="kind">Type</SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </FieldContent>
                </Field>

                <Field>
                  <FieldLabel>Direction</FieldLabel>
                  <FieldContent>
                    <Select
                      onValueChange={(value) =>
                        setSortDirection(value as "asc" | "desc")
                      }
                      value={sortDirection}
                    >
                      <SelectTrigger className="w-full sm:w-32">
                        <SelectValue placeholder="Direction" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectItem value="asc">Ascending</SelectItem>
                          <SelectItem value="desc">Descending</SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </FieldContent>
                </Field>

                <Field>
                  <FieldLabel>Page size</FieldLabel>
                  <FieldContent>
                    <Select
                      onValueChange={(value) => setPageSize(Number(value))}
                      value={String(pageSize)}
                    >
                      <SelectTrigger className="w-full sm:w-24">
                        <SelectValue placeholder="Size" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          {PAGE_SIZE_OPTIONS.map((size) => (
                            <SelectItem key={size} value={size}>
                              {size}
                            </SelectItem>
                          ))}
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </FieldContent>
                </Field>
              </div>

              {workspacePending && !contents ? (
                <div className="flex flex-col gap-3">
                  <Skeleton className="h-12 rounded-2xl" />
                  <Skeleton className="h-12 rounded-2xl" />
                  <Skeleton className="h-12 rounded-2xl" />
                </div>
              ) : paginatedItems.length > 0 ? (
                <>
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
                        {paginatedItems.map((item) => (
                          <TableRow key={`${item.kind}-${item.id}`}>
                            <TableCell className="font-medium">
                              {item.name}
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant={
                                  item.kind === "folder" ? "outline" : "default"
                                }
                              >
                                {item.kind === "folder"
                                  ? "Folder"
                                  : item.status}
                              </Badge>
                            </TableCell>
                            <TableCell>{formatDate(item.updatedAt)}</TableCell>
                            <TableCell>
                              {item.size === null
                                ? "-"
                                : formatBytes(item.size)}
                            </TableCell>
                            <TableCell className="text-right">
                              {item.kind === "folder" ? (
                                <Button
                                  onClick={() => void openFolder(item.id)}
                                  size="sm"
                                  variant="outline"
                                >
                                  <FolderIcon data-icon="inline-start" />
                                  Open
                                </Button>
                              ) : (
                                <Button
                                  onClick={() =>
                                    void handleDownload(item.id, item.name)
                                  }
                                  size="sm"
                                  variant="outline"
                                >
                                  <ArrowDownToLineIcon data-icon="inline-start" />
                                  Download
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-sm text-muted-foreground">
                      Showing {(pageIndex - 1) * pageSize + 1} to{" "}
                      {Math.min(pageIndex * pageSize, sortedItems.length)} of{" "}
                      {sortedItems.length} items
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        disabled={pageIndex === 1}
                        onClick={() =>
                          setPageIndex((current) => Math.max(1, current - 1))
                        }
                        variant="outline"
                      >
                        Previous
                      </Button>
                      <Badge variant="outline">
                        Page {pageIndex} of {totalPages}
                      </Badge>
                      <Button
                        disabled={pageIndex >= totalPages}
                        onClick={() =>
                          setPageIndex((current) =>
                            Math.min(totalPages, current + 1),
                          )
                        }
                        variant="outline"
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </>
              ) : (
                <Empty className="border bg-muted/20">
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      {searchQuery ? (
                        <ChevronsLeftRightEllipsisIcon />
                      ) : (
                        <ShieldCheckIcon />
                      )}
                    </EmptyMedia>
                    <EmptyTitle>
                      {searchQuery
                        ? "No items match this search"
                        : "This folder is empty"}
                    </EmptyTitle>
                    <EmptyDescription>
                      {searchQuery
                        ? "Try a different search query, sort order, or page size."
                        : "Create a folder, upload a file, or open the share manager to continue."}
                    </EmptyDescription>
                  </EmptyHeader>
                  <EmptyContent />
                </Empty>
              )}
            </CardContent>
          </Card>
        </main>
      </div>
    </>
  );
}

function FolderTree({
  activeFolderId,
  expandedFolderIds,
  nodes,
  onOpenFolder,
  onToggleFolder,
  rootFolderId,
}: {
  activeFolderId: string | null;
  expandedFolderIds: Set<string>;
  nodes: Record<string, FolderNode>;
  onOpenFolder: (folderId: string) => Promise<void>;
  onToggleFolder: (folderId: string) => Promise<void>;
  rootFolderId: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <FolderTreeNode
        activeFolderId={activeFolderId}
        depth={0}
        expandedFolderIds={expandedFolderIds}
        folderId={rootFolderId}
        nodes={nodes}
        onOpenFolder={onOpenFolder}
        onToggleFolder={onToggleFolder}
      />
    </div>
  );
}

function FolderTreeNode({
  activeFolderId,
  depth,
  expandedFolderIds,
  folderId,
  nodes,
  onOpenFolder,
  onToggleFolder,
}: {
  activeFolderId: string | null;
  depth: number;
  expandedFolderIds: Set<string>;
  folderId: string;
  nodes: Record<string, FolderNode>;
  onOpenFolder: (folderId: string) => Promise<void>;
  onToggleFolder: (folderId: string) => Promise<void>;
}) {
  const node = nodes[folderId];
  if (!node) {
    return null;
  }

  const isExpanded = expandedFolderIds.has(folderId);
  const hasChildren = node.childFolderIds.length > 0;

  return (
    <div className="flex flex-col gap-1">
      <div
        className="flex items-center gap-1 rounded-xl px-2 py-1.5"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        <Button
          className="shrink-0"
          onClick={() => void onToggleFolder(folderId)}
          size="icon-xs"
          variant="ghost"
        >
          <ChevronRightIcon
            className={
              isExpanded
                ? "rotate-90 transition-transform"
                : "transition-transform"
            }
          />
        </Button>
        <Button
          className="flex-1 justify-start truncate"
          onClick={() => void onOpenFolder(folderId)}
          variant={activeFolderId === folderId ? "secondary" : "ghost"}
        >
          <FolderIcon data-icon="inline-start" />
          {node.folder.name}
        </Button>
      </div>

      {isExpanded && hasChildren ? (
        <div className="flex flex-col gap-1">
          {node.childFolderIds.map((childFolderId) => (
            <FolderTreeNode
              activeFolderId={activeFolderId}
              depth={depth + 1}
              expandedFolderIds={expandedFolderIds}
              folderId={childFolderId}
              key={childFolderId}
              nodes={nodes}
              onOpenFolder={onOpenFolder}
              onToggleFolder={onToggleFolder}
            />
          ))}
        </div>
      ) : null}
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
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected error";
}

function toAbsoluteUrl(pathname: string): string {
  return new URL(pathname, window.location.origin).toString();
}
