import {
  Fragment,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ArrowDownToLineIcon,
  ChevronRightIcon,
  FolderIcon,
  FolderOpenIcon,
  FolderPlusIcon,
  Link2Icon,
  Loader2Icon,
  LogOutIcon,
  MoreHorizontalIcon,
  SearchIcon,
  SparklesIcon,
  UploadIcon,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
  Empty,
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
  type FileSummary,
  type Folder,
  type FolderContents,
  type ResourceSearchItem,
  type ResourceSearchResponse,
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
  searchResources,
  updateFolderShare,
  uploadFile,
} from "@/lib/api";
import { formatBytes, formatDate, getInitials } from "@/lib/format";

type FolderNode = {
  folder: Folder;
  childFolderIds: string[];
};

type SortKey = "name" | "updated_at" | "size" | "type";

const PAGE_SIZE_OPTIONS = ["8", "16", "24"];

export function WorkspaceScreen() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const searchRequestIdRef = useRef(0);
  const lastSearchSignatureRef = useRef<string | null>(null);

  const [rootFolderId, setRootFolderId] = useState<string | null>(null);
  const [contents, setContents] = useState<FolderContents | null>(null);
  const [resourceResults, setResourceResults] =
    useState<ResourceSearchResponse | null>(null);
  const [share, setShare] = useState<Share | null>(null);
  const [workspacePending, setWorkspacePending] = useState(false);
  const [resourcePending, setResourcePending] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [folderPending, setFolderPending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sharePending, setSharePending] = useState(false);
  const [shareSheetOpen, setShareSheetOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const deferredSearchQuery = useDeferredValue(searchQuery);
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [pageSize, setPageSize] = useState(8);
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
    if (!accessToken || !contents) {
      return;
    }

    void loadResourceResults(accessToken, contents.folder.id);
  }, [
    accessToken,
    contents?.folder.id,
    deferredSearchQuery,
    pageIndex,
    pageSize,
    sortDirection,
    sortKey,
  ]);

  useEffect(() => {
    setPageIndex(1);
  }, [
    contents?.folder.id,
    deferredSearchQuery,
    pageSize,
    sortDirection,
    sortKey,
  ]);

  const folderItems = useMemo(
    () =>
      (resourceResults?.items ?? []).filter(
        (item): item is Extract<ResourceSearchItem, { item_type: "FOLDER" }> =>
          item.item_type === "FOLDER",
      ),
    [resourceResults],
  );
  const fileItems = useMemo(
    () =>
      (resourceResults?.items ?? []).filter(
        (item): item is Extract<ResourceSearchItem, { item_type: "FILE" }> =>
          item.item_type === "FILE",
      ),
    [resourceResults],
  );

  const breadcrumbFolders = useMemo(() => {
    if (!contents) {
      return [];
    }

    const chain: Folder[] = [];
    let currentFolder: Folder | undefined = contents.folder;

    while (currentFolder) {
      chain.unshift(currentFolder);
      currentFolder = currentFolder.parent_id
        ? folderTree[currentFolder.parent_id]?.folder
        : undefined;
    }

    return chain;
  }, [contents, folderTree]);

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
      await loadResourceResults(token, targetFolderId, { force: true });
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

  async function loadResourceResults(
    token: string,
    folderId: string,
    options?: { force?: boolean },
  ) {
    const querySignature = JSON.stringify({
      folderId,
      order: sortDirection,
      page: pageIndex,
      pageSize,
      q: deferredSearchQuery.trim(),
      sortKey,
    });

    if (!options?.force && lastSearchSignatureRef.current === querySignature) {
      return;
    }

    lastSearchSignatureRef.current = querySignature;
    const requestId = searchRequestIdRef.current + 1;
    searchRequestIdRef.current = requestId;
    setResourcePending(true);

    try {
      const nextResults = await searchResources(token, {
        parent_id: folderId,
        order: sortDirection,
        page: pageIndex,
        page_size: pageSize,
        q: deferredSearchQuery.trim(),
        sort_by: sortKey,
      });

      if (searchRequestIdRef.current !== requestId) {
        return;
      }

      setResourceResults(nextResults);
    } catch (error) {
      if (searchRequestIdRef.current === requestId) {
        lastSearchSignatureRef.current = null;
        setWorkspaceError(getErrorMessage(error));
      }
    } finally {
      if (searchRequestIdRef.current === requestId) {
        setResourcePending(false);
      }
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
    if (!contents || !token || !newFolderName.trim()) {
      return;
    }

    setFolderPending(true);
    try {
      await createFolder(token, {
        name: newFolderName.trim(),
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

  function openNativeFilePicker() {
    uploadInputRef.current?.click();
  }

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

      <input
        className="hidden"
        onChange={(event) => void handleUpload(event)}
        ref={uploadInputRef}
        type="file"
      />

      <div className="grid gap-6 xl:grid-cols-[280px_1fr]">
        <aside className="flex flex-col gap-4">
          <Card className="rounded-[2rem] border-border/70 bg-card/95">
            <CardHeader className="gap-5">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <Avatar className="size-11">
                    <AvatarFallback>
                      {getInitials(user.nickname)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0">
                    <CardTitle className="truncate text-base">
                      {user.nickname}
                    </CardTitle>
                    <CardDescription className="truncate">
                      @{user.username}
                    </CardDescription>
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

              <div className="rounded-[1.5rem] border bg-muted/35 p-4">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <SparklesIcon className="text-muted-foreground" />
                  Workspace summary
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <MetricPill
                    label="Folders"
                    value={String(contents?.folders.length ?? 0)}
                  />
                  <MetricPill
                    label="Files"
                    value={String(contents?.files.length ?? 0)}
                  />
                </div>
              </div>
            </CardHeader>
          </Card>

          <Card className="rounded-[2rem] border-border/70 bg-card/95">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Navigation</CardTitle>
              <CardDescription>
                Right click any folder in the tree to open it or expand it in
                place.
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

        <ContextMenu>
          <ContextMenuTrigger>
            <main className="flex flex-col gap-4">
              <Card className="rounded-[2rem] border-border/70 bg-card/95">
                <CardHeader className="gap-4 pb-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="flex min-w-0 flex-col gap-3">
                      <Breadcrumb>
                        <BreadcrumbList>
                          {breadcrumbFolders.length > 0 ? (
                            breadcrumbFolders.map((folder, index) => {
                              const isLast =
                                index === breadcrumbFolders.length - 1;

                              return (
                                <Fragment key={folder.id}>
                                  <BreadcrumbItem>
                                    {isLast ? (
                                      <BreadcrumbPage>
                                        {folder.name}
                                      </BreadcrumbPage>
                                    ) : (
                                      <BreadcrumbLink
                                        className="cursor-pointer"
                                        onClick={() =>
                                          void openFolder(folder.id)
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
                              <BreadcrumbPage>Workspace</BreadcrumbPage>
                            </BreadcrumbItem>
                          )}
                        </BreadcrumbList>
                      </Breadcrumb>
                      <div>
                        <CardTitle className="text-2xl tracking-tight">
                          File management
                        </CardTitle>
                        <CardDescription className="mt-1">
                          Browse the current folder, search quickly, and use
                          right click for item actions.
                        </CardDescription>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        onClick={() => setShareSheetOpen(true)}
                        variant={share ? "outline" : "default"}
                      >
                        <Link2Icon data-icon="inline-start" />
                        Manage share
                      </Button>
                      <Button onClick={openNativeFilePicker} variant="outline">
                        <UploadIcon data-icon="inline-start" />
                        Upload
                      </Button>
                    </div>
                  </div>

                  <div className="grid gap-3 lg:grid-cols-[1fr_160px_150px_120px]">
                    <Field>
                      <FieldLabel htmlFor="workspace-search">Search</FieldLabel>
                      <FieldContent>
                        <div className="relative">
                          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                          <Input
                            className="pl-9"
                            id="workspace-search"
                            onChange={(event) =>
                              setSearchQuery(event.target.value)
                            }
                            placeholder="Search by folder or file name"
                            value={searchQuery}
                          />
                        </div>
                      </FieldContent>
                    </Field>

                    <Field>
                      <FieldLabel>Sort by</FieldLabel>
                      <FieldContent>
                        <Select
                          onValueChange={(value) =>
                            setSortKey(value as SortKey)
                          }
                          value={sortKey}
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Sort field" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectGroup>
                              <SelectItem value="name">Name</SelectItem>
                              <SelectItem value="updated_at">
                                Updated
                              </SelectItem>
                              <SelectItem value="size">Size</SelectItem>
                              <SelectItem value="type">Type</SelectItem>
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
                          <SelectTrigger className="w-full">
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
                          <SelectTrigger className="w-full">
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
                </CardHeader>
              </Card>

              {workspaceError ? (
                <Alert variant="destructive">
                  <AlertTitle>Workspace load failed</AlertTitle>
                  <AlertDescription>{workspaceError}</AlertDescription>
                </Alert>
              ) : null}

              <Card className="rounded-[2rem] border-border/70 bg-card/95">
                <CardHeader className="gap-5 pb-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <CardTitle className="text-lg">Quick create</CardTitle>
                      <CardDescription>
                        Keep the main flow lightweight. Use this bar for
                        creation and right click for item actions.
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      {share ? (
                        <Badge variant="outline">
                          {share.permission_level}
                        </Badge>
                      ) : null}
                      <Badge variant={share ? "default" : "secondary"}>
                        {share ? "Active share" : "No share"}
                      </Badge>
                    </div>
                  </div>

                  <form
                    className="grid gap-3 md:grid-cols-[1fr_auto]"
                    onSubmit={handleCreateFolder}
                  >
                    <Field>
                      <FieldLabel htmlFor="new-folder-name">
                        New folder
                      </FieldLabel>
                      <FieldContent>
                        <Input
                          id="new-folder-name"
                          onChange={(event) =>
                            setNewFolderName(event.target.value)
                          }
                          placeholder="Enter a folder name"
                          value={newFolderName}
                        />
                        <FieldDescription>
                          Name validation and permission checks still come from
                          the backend.
                        </FieldDescription>
                      </FieldContent>
                    </Field>
                    <div className="flex items-end">
                      <Button
                        className="w-full md:w-auto"
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
                    </div>
                  </form>
                </CardHeader>

                <CardContent className="flex flex-col gap-6">
                  {workspacePending && !contents ? (
                    <div className="grid gap-3">
                      <Skeleton className="h-28 rounded-2xl" />
                      <Skeleton className="h-16 rounded-2xl" />
                      <Skeleton className="h-16 rounded-2xl" />
                    </div>
                  ) : (resourceResults?.pagination.total_items ?? 0) === 0 ? (
                    <Empty className="border bg-muted/20 py-16">
                      <EmptyHeader>
                        <EmptyMedia variant="icon">
                          {searchQuery ? <SearchIcon /> : <FolderOpenIcon />}
                        </EmptyMedia>
                        <EmptyTitle>
                          {searchQuery
                            ? "No items match this search"
                            : "This folder is empty"}
                        </EmptyTitle>
                        <EmptyDescription>
                          {searchQuery
                            ? "Try a different query, sort order, or page size."
                            : "Upload a file, create a folder, or open the share manager to keep moving."}
                        </EmptyDescription>
                      </EmptyHeader>
                    </Empty>
                  ) : (
                    <>
                      <section className="flex flex-col gap-4">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <h3 className="text-sm font-medium text-foreground">
                              Folders
                            </h3>
                            <p className="text-sm text-muted-foreground">
                              Double down on navigation here. Right click for
                              folder actions.
                            </p>
                          </div>
                          <Badge variant="outline">
                            {folderItems.length} on this page
                          </Badge>
                        </div>

                        {folderItems.length > 0 ? (
                          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                            {folderItems.map((item) => (
                              <FolderCard
                                active={contents?.folder.id === item.folder.id}
                                folder={item.folder}
                                onOpen={() => void openFolder(item.folder.id)}
                                onToggleInTree={() =>
                                  void toggleFolderExpansion(item.folder.id)
                                }
                              />
                            ))}
                          </div>
                        ) : (
                          <div className="rounded-[1.5rem] border border-dashed p-6 text-sm text-muted-foreground">
                            No folders are visible on this page.
                          </div>
                        )}
                      </section>

                      <Separator />

                      <section className="flex flex-col gap-4">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <h3 className="text-sm font-medium text-foreground">
                              Files
                            </h3>
                            <p className="text-sm text-muted-foreground">
                              Keep the table focused on content. Downloads and
                              item actions live on right click.
                            </p>
                          </div>
                          <Badge variant="outline">
                            {fileItems.length} on this page
                          </Badge>
                        </div>

                        {fileItems.length > 0 ? (
                          <div className="overflow-hidden rounded-[1.5rem] border">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Name</TableHead>
                                  <TableHead>Status</TableHead>
                                  <TableHead>Updated</TableHead>
                                  <TableHead>Size</TableHead>
                                  <TableHead className="text-right">
                                    Quick action
                                  </TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {fileItems.map((item) => (
                                  <FileRow
                                    file={item.file}
                                    onDownload={() =>
                                      void handleDownload(
                                        item.file.id,
                                        item.file.stored_filename,
                                      )
                                    }
                                  />
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        ) : (
                          <div className="rounded-[1.5rem] border border-dashed p-6 text-sm text-muted-foreground">
                            No files are visible on this page.
                          </div>
                        )}
                      </section>
                    </>
                  )}
                </CardContent>
              </Card>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-muted-foreground">
                  Showing{" "}
                  {resourceResults?.pagination.total_items
                    ? (pageIndex - 1) * pageSize + 1
                    : 0}{" "}
                  to{" "}
                  {Math.min(
                    pageIndex * pageSize,
                    resourceResults?.pagination.total_items ?? 0,
                  )}{" "}
                  of {resourceResults?.pagination.total_items ?? 0} items
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    disabled={pageIndex === 1 || resourcePending}
                    onClick={() =>
                      setPageIndex((current) => Math.max(1, current - 1))
                    }
                    variant="outline"
                  >
                    Previous
                  </Button>
                  <Badge variant="outline">
                    Page {pageIndex} of{" "}
                    {resourceResults?.pagination.total_pages ?? 1}
                  </Badge>
                  <Button
                    disabled={
                      resourcePending ||
                      pageIndex >=
                        (resourceResults?.pagination.total_pages ?? 1)
                    }
                    onClick={() =>
                      setPageIndex((current) =>
                        Math.min(
                          resourceResults?.pagination.total_pages ?? 1,
                          current + 1,
                        ),
                      )
                    }
                    variant="outline"
                  >
                    Next
                  </Button>
                </div>
              </div>
            </main>
          </ContextMenuTrigger>

          <ContextMenuContent>
            <ContextMenuItem onClick={() => void setShareSheetOpen(true)}>
              <Link2Icon />
              Manage current folder share
            </ContextMenuItem>
            <ContextMenuItem onClick={openNativeFilePicker}>
              <UploadIcon />
              Upload a file
            </ContextMenuItem>
            <ContextMenuSeparator />
            <ContextMenuItem
              onClick={() =>
                document.getElementById("new-folder-name")?.focus()
              }
            >
              <FolderPlusIcon />
              Focus new folder input
            </ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>
      </div>
    </>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border bg-background/80 px-3 py-3">
      <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
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

  return (
    <div className="flex flex-col gap-1">
      <ContextMenu>
        <ContextMenuTrigger>
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
        </ContextMenuTrigger>
        <ContextMenuContent>
          <ContextMenuItem onClick={() => void onOpenFolder(folderId)}>
            <FolderOpenIcon />
            Open folder
          </ContextMenuItem>
          <ContextMenuItem onClick={() => void onToggleFolder(folderId)}>
            <ChevronRightIcon />
            Toggle branch
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>

      {isExpanded && node.childFolderIds.length > 0 ? (
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

function FolderCard({
  active,
  folder,
  onOpen,
  onToggleInTree,
}: {
  active: boolean;
  folder: Folder;
  onOpen: () => void;
  onToggleInTree: () => void;
}) {
  return (
    <ContextMenu>
      <ContextMenuTrigger>
        <button
          className="group flex w-full flex-col items-start gap-4 rounded-[1.5rem] border bg-background/85 p-4 text-left transition-colors hover:bg-muted/30"
          onClick={onOpen}
          type="button"
        >
          <div className="flex w-full items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-2xl bg-muted text-foreground">
                <FolderIcon />
              </div>
              <div className="min-w-0">
                <p className="truncate font-medium text-foreground">
                  {folder.name}
                </p>
                <p className="text-sm text-muted-foreground">
                  Updated {formatDate(folder.updated_at)}
                </p>
              </div>
            </div>
            <MoreHorizontalIcon className="text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
          </div>

          <div className="flex items-center gap-2">
            {active ? (
              <Badge>Current</Badge>
            ) : (
              <Badge variant="outline">Folder</Badge>
            )}
          </div>
        </button>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onClick={onOpen}>
          <FolderOpenIcon />
          Open folder
        </ContextMenuItem>
        <ContextMenuItem onClick={onToggleInTree}>
          <ChevronRightIcon />
          Toggle in tree
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

function FileRow({
  file,
  onDownload,
}: {
  file: FileSummary;
  onDownload: () => void;
}) {
  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <TableRow className="cursor-default">
          <TableCell className="font-medium">{file.stored_filename}</TableCell>
          <TableCell>
            <Badge>{file.status}</Badge>
          </TableCell>
          <TableCell>{formatDate(file.updated_at)}</TableCell>
          <TableCell>{formatBytes(file.size_bytes)}</TableCell>
          <TableCell className="text-right">
            <Button onClick={onDownload} size="sm" variant="ghost">
              <ArrowDownToLineIcon data-icon="inline-start" />
              Download
            </Button>
          </TableCell>
        </TableRow>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onClick={onDownload}>
          <ArrowDownToLineIcon />
          Download file
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
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
