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
  ArrowRightLeftIcon,
  FileTextIcon,
  FolderIcon,
  FolderInputIcon,
  FolderOpenIcon,
  Link2Icon,
  Loader2Icon,
  LogOutIcon,
  PencilIcon,
  SearchIcon,
  SparklesIcon,
  TrashIcon,
  UploadIcon,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  deleteFile,
  deleteFolder,
  downloadFile,
  getFolderContents,
  getFolderShare,
  getRootFolder,
  moveFile,
  moveFolder,
  renameFile,
  renameFolder,
  revokeFolderShare,
  searchResources,
  updateFolderShare,
  uploadFile,
} from "@/lib/api";
import { formatBytes, formatDate, getInitials } from "@/lib/format";

type SortKey = "name" | "updated_at" | "size" | "type";

type ActionResource =
  | {
      kind: "folder";
      id: string;
      name: string;
      parentId: string | null;
      pathCache: string | null;
    }
  | {
      kind: "file";
      id: string;
      name: string;
      parentId: string;
    };

type EditDialogState =
  | { mode: "create-folder"; parentId: string }
  | { mode: "rename"; resource: ActionResource }
  | { mode: "move"; resource: ActionResource }
  | null;

type ToolbarProps = {
  breadcrumbFolders: Folder[];
  onOpenFolder: (folderId: string) => Promise<void>;
  pageSize: number;
  searchQuery: string;
  setPageSize: (value: number) => void;
  setSearchQuery: (value: string) => void;
  setSortDirection: (value: "asc" | "desc") => void;
  setSortKey: (value: SortKey) => void;
  share: Share | null;
  sortDirection: "asc" | "desc";
  sortKey: SortKey;
};

type WorkspaceResultsProps = {
  contents: FolderContents | null;
  currentFolderId: string;
  onDeleteResource: (resource: ActionResource) => void;
  onDownloadFile: (fileId: string, filename: string) => Promise<void>;
  onEditResource: (state: EditDialogState) => void;
  onOpenFolder: (folderId: string) => Promise<void>;
  resourceResults: ResourceSearchResponse | null;
  searchQuery: string;
  workspacePending: boolean;
};

type WorkspaceRowProps = {
  item: ResourceSearchItem;
  onDelete: () => void;
  onDownload: () => void;
  onMove: () => void;
  onOpenFolder: () => void;
  onRename: () => void;
};

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
  const [sharePending, setSharePending] = useState(false);
  const [shareSheetOpen, setShareSheetOpen] = useState(false);
  const [editDialogState, setEditDialogState] = useState<EditDialogState>(null);
  const [deleteDialogResource, setDeleteDialogResource] =
    useState<ActionResource | null>(null);
  const [actionPending, setActionPending] = useState(false);
  const [resourceName, setResourceName] = useState("");
  const [moveTargetId, setMoveTargetId] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const deferredSearchQuery = useDeferredValue(searchQuery);
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [pageSize, setPageSize] = useState(8);
  const [pageIndex, setPageIndex] = useState(1);
  const [knownFolders, setKnownFolders] = useState<Record<string, Folder>>({});

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

  const workspaceItems = resourceResults?.items ?? [];
  const currentFolderId = contents?.folder.id ?? "";

  const breadcrumbFolders = useMemo(() => {
    if (!contents) {
      return [];
    }

    const chain: Folder[] = [];
    let currentFolder: Folder | undefined = contents.folder;

    while (currentFolder) {
      chain.unshift(currentFolder);
      currentFolder = currentFolder.parent_id
        ? knownFolders[currentFolder.parent_id]
        : undefined;
    }

    return chain;
  }, [contents, knownFolders]);

  const moveTargets = useMemo(() => {
    const folders = Object.values(knownFolders).sort((left, right) =>
      (left.path_cache ?? left.name).localeCompare(
        right.path_cache ?? right.name,
        undefined,
        { sensitivity: "base" },
      ),
    );

    if (!editDialogState || editDialogState.mode === "create-folder") {
      return folders;
    }

    const activeResource = editDialogState.resource;
    const currentFolderPath =
      activeResource.kind === "folder" ? activeResource.pathCache : null;

    return folders.filter((folder) => {
      if (activeResource.kind === "file") {
        return folder.id !== activeResource.parentId;
      }

      if (folder.id === activeResource.id) {
        return false;
      }

      if (
        currentFolderPath &&
        folder.path_cache &&
        (folder.path_cache === currentFolderPath ||
          folder.path_cache.startsWith(`${currentFolderPath}/`))
      ) {
        return false;
      }

      return true;
    });
  }, [editDialogState, knownFolders]);

  useEffect(() => {
    if (!editDialogState) {
      setResourceName("");
      setMoveTargetId("");
      return;
    }

    if (editDialogState.mode === "create-folder") {
      setResourceName("");
      setMoveTargetId("");
      return;
    }

    setResourceName(editDialogState.resource.name);
    setMoveTargetId(
      editDialogState.mode === "move" ? (moveTargets[0]?.id ?? "") : "",
    );
  }, [editDialogState, moveTargets]);

  if (!accessToken || !user) {
    return null;
  }

  const authToken = accessToken;

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
      registerFolders(nextContents.folder, nextContents.folders);
      await loadResourceResults(token, targetFolderId, { force: true });
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

  function registerFolders(folder: Folder, childFolders: Folder[]) {
    setKnownFolders((current) => {
      const next = { ...current, [folder.id]: folder };

      for (const childFolder of childFolders) {
        next[childFolder.id] = childFolder;
      }

      return next;
    });
  }

  async function openFolder(folderId: string) {
    await loadWorkspace(authToken, folderId);
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !contents) {
      return;
    }

    try {
      await uploadFile(authToken, contents.folder.id, file);
      await loadWorkspace(authToken, contents.folder.id);
      toast.success(`${file.name} uploaded`);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      event.target.value = "";
    }
  }

  async function handleDownload(fileId: string, filename: string) {
    try {
      const blob = await downloadFile(authToken, fileId);
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
    if (!contents) {
      return;
    }

    const normalizedValues = shareFormSchema.parse(values);
    setSharePending(true);

    try {
      const nextShare = share
        ? await updateFolderShare(
            authToken,
            contents.folder.id,
            normalizedValues,
          )
        : await createFolderShare(
            authToken,
            contents.folder.id,
            normalizedValues,
          );

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
    if (!contents || !share) {
      return;
    }

    setSharePending(true);

    try {
      await revokeFolderShare(authToken, contents.folder.id);
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

  async function handleSaveResourceAction() {
    if (!editDialogState || !contents) {
      return;
    }

    setActionPending(true);

    try {
      if (editDialogState.mode === "create-folder") {
        if (!resourceName.trim()) {
          toast.error("Enter a valid folder name.");
          return;
        }

        await createFolder(authToken, {
          name: resourceName.trim(),
          parent_id: editDialogState.parentId,
        });
        toast.success("Folder created");
      } else if (editDialogState.mode === "rename") {
        if (!resourceName.trim()) {
          toast.error("Enter a valid name.");
          return;
        }

        if (editDialogState.resource.kind === "folder") {
          await renameFolder(authToken, editDialogState.resource.id, {
            name: resourceName.trim(),
          });
          toast.success("Folder renamed");
        } else {
          await renameFile(authToken, editDialogState.resource.id, {
            filename: resourceName.trim(),
          });
          toast.success("File renamed");
        }
      } else {
        if (!moveTargetId) {
          toast.error("Choose a destination folder.");
          return;
        }

        if (editDialogState.resource.kind === "folder") {
          await moveFolder(authToken, editDialogState.resource.id, {
            target_parent_id: moveTargetId,
          });
          toast.success("Folder moved");
        } else {
          await moveFile(authToken, editDialogState.resource.id, {
            target_folder_id: moveTargetId,
          });
          toast.success("File moved");
        }
      }

      setEditDialogState(null);
      await loadWorkspace(authToken, contents.folder.id);
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setActionPending(false);
    }
  }

  async function handleDeleteResource() {
    const resource = deleteDialogResource;
    if (!resource) {
      return;
    }

    setActionPending(true);

    try {
      if (resource.kind === "folder") {
        await deleteFolder(authToken, resource.id);
        toast.success("Folder deleted");
      } else {
        await deleteFile(authToken, resource.id);
        toast.success("File deleted");
      }

      setDeleteDialogResource(null);

      if (
        resource.kind === "folder" &&
        contents?.folder.id === resource.id &&
        resource.parentId
      ) {
        await loadWorkspace(authToken, resource.parentId);
      } else {
        await loadWorkspace(authToken, contents?.folder.id);
      }
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setActionPending(false);
    }
  }

  return (
    <>
      <WorkspaceActionDialog
        actionPending={actionPending}
        editDialogState={editDialogState}
        moveTargetId={moveTargetId}
        moveTargets={moveTargets}
        onOpenChange={setEditDialogState}
        onSave={() => void handleSaveResourceAction()}
        resourceName={resourceName}
        setMoveTargetId={setMoveTargetId}
        setResourceName={setResourceName}
      />

      <DeleteResourceDialog
        actionPending={actionPending}
        deleteDialogResource={deleteDialogResource}
        onConfirm={() => void handleDeleteResource()}
        onOpenChange={setDeleteDialogResource}
      />

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

      <div className="flex flex-col gap-6">
        <header className="sticky top-4 z-40">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 rounded-full border border-border/70 bg-background/78 px-3 py-3 shadow-lg shadow-black/5 ring-1 ring-white/55 backdrop-blur-xl sm:px-5">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-full bg-foreground text-background">
                <SparklesIcon />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold tracking-[0.22em] text-foreground uppercase">
                  filesh
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Avatar className="size-10 border border-border/70 bg-card">
                <AvatarFallback>{getInitials(user.nickname)}</AvatarFallback>
              </Avatar>
              <div className="hidden min-w-0 sm:block">
                <p className="truncate text-sm font-medium text-foreground">
                  {user.nickname}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  @{user.username}
                </p>
              </div>
              <Button
                className="rounded-full"
                onClick={() => void logout()}
                size="icon"
                variant="outline"
              >
                <LogOutIcon data-icon="inline-start" />
                <span className="sr-only">Log out</span>
              </Button>
            </div>
          </div>
        </header>

        <ContextMenu>
          <ContextMenuTrigger>
            <main className="flex min-w-0 flex-col gap-6">
              <WorkspaceToolbar
                breadcrumbFolders={breadcrumbFolders}
                onOpenFolder={openFolder}
                pageSize={pageSize}
                searchQuery={searchQuery}
                setPageSize={setPageSize}
                setSearchQuery={setSearchQuery}
                setSortDirection={setSortDirection}
                setSortKey={setSortKey}
                share={share}
                sortDirection={sortDirection}
                sortKey={sortKey}
              />

              {workspaceError ? (
                <Alert variant="destructive">
                  <AlertTitle>Workspace load failed</AlertTitle>
                  <AlertDescription>{workspaceError}</AlertDescription>
                </Alert>
              ) : null}

              <WorkspaceResults
                contents={contents}
                currentFolderId={currentFolderId}
                onDeleteResource={setDeleteDialogResource}
                onDownloadFile={handleDownload}
                onEditResource={setEditDialogState}
                onOpenFolder={openFolder}
                resourceResults={resourceResults}
                searchQuery={searchQuery}
                workspacePending={workspacePending}
              />

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
            <ContextMenuItem
              onClick={() =>
                setEditDialogState({
                  mode: "create-folder",
                  parentId: currentFolderId,
                })
              }
            >
              <FolderInputIcon />
              Create folder
            </ContextMenuItem>
            <ContextMenuItem onClick={() => setShareSheetOpen(true)}>
              <Link2Icon />
              Manage current folder share
            </ContextMenuItem>
            <ContextMenuItem onClick={openNativeFilePicker}>
              <UploadIcon />
              Upload a file
            </ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>
      </div>
    </>
  );
}

function WorkspaceActionDialog({
  actionPending,
  editDialogState,
  moveTargetId,
  moveTargets,
  onOpenChange,
  onSave,
  resourceName,
  setMoveTargetId,
  setResourceName,
}: {
  actionPending: boolean;
  editDialogState: EditDialogState;
  moveTargetId: string;
  moveTargets: Folder[];
  onOpenChange: (state: EditDialogState) => void;
  onSave: () => void;
  resourceName: string;
  setMoveTargetId: (value: string) => void;
  setResourceName: (value: string) => void;
}) {
  const isRename = editDialogState?.mode === "rename";
  const isCreateFolder = editDialogState?.mode === "create-folder";
  const isMove = editDialogState?.mode === "move";

  return (
    <Dialog
      onOpenChange={(open) => {
        if (!open && !actionPending) {
          onOpenChange(null);
        }
      }}
      open={editDialogState !== null}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isCreateFolder
              ? "Create folder"
              : isRename
                ? `Rename ${editDialogState?.resource.kind ?? "resource"}`
                : `Move ${editDialogState?.resource.kind ?? "resource"}`}
          </DialogTitle>
          <DialogDescription>
            {isCreateFolder
              ? "Create a new folder in the current location."
              : isRename
                ? "Update the visible name used in the workspace."
                : "Choose a destination from the folders currently known to the workspace."}
          </DialogDescription>
        </DialogHeader>

        {isCreateFolder || isRename ? (
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="resource-name">Name</FieldLabel>
              <FieldContent>
                <Input
                  id="resource-name"
                  onChange={(event) => setResourceName(event.target.value)}
                  placeholder={
                    isCreateFolder ? "Enter a folder name" : "Enter a new name"
                  }
                  value={resourceName}
                />
              </FieldContent>
            </Field>
          </FieldGroup>
        ) : (
          <FieldGroup>
            <Field>
              <FieldLabel>Destination folder</FieldLabel>
              <FieldContent>
                <Select onValueChange={setMoveTargetId} value={moveTargetId}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select a destination" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {moveTargets.map((folder) => (
                        <SelectItem key={folder.id} value={folder.id}>
                          {folder.path_cache || folder.name}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
                <FieldDescription>
                  Open folders as you work to expand the list of available
                  destinations.
                </FieldDescription>
              </FieldContent>
            </Field>
          </FieldGroup>
        )}

        <DialogFooter>
          <Button
            disabled={actionPending}
            onClick={() => onOpenChange(null)}
            variant="outline"
          >
            Cancel
          </Button>
          <Button
            disabled={
              actionPending || (isMove ? !moveTargetId : !resourceName.trim())
            }
            onClick={onSave}
          >
            {actionPending ? (
              <Loader2Icon className="animate-spin" data-icon="inline-start" />
            ) : isMove ? (
              <ArrowRightLeftIcon data-icon="inline-start" />
            ) : isCreateFolder ? (
              <FolderInputIcon data-icon="inline-start" />
            ) : (
              <PencilIcon data-icon="inline-start" />
            )}
            {isCreateFolder
              ? "Create folder"
              : isRename
                ? "Save changes"
                : "Move"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteResourceDialog({
  actionPending,
  deleteDialogResource,
  onConfirm,
  onOpenChange,
}: {
  actionPending: boolean;
  deleteDialogResource: ActionResource | null;
  onConfirm: () => void;
  onOpenChange: (resource: ActionResource | null) => void;
}) {
  return (
    <AlertDialog
      onOpenChange={(open) => {
        if (!open && !actionPending) {
          onOpenChange(null);
        }
      }}
      open={deleteDialogResource !== null}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete resource</AlertDialogTitle>
          <AlertDialogDescription>
            {deleteDialogResource
              ? `Delete ${deleteDialogResource.name}? This action cannot be undone.`
              : "This action cannot be undone."}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={actionPending}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            disabled={actionPending}
            onClick={(event) => {
              event.preventDefault();
              onConfirm();
            }}
          >
            {actionPending ? (
              <Loader2Icon className="animate-spin" data-icon="inline-start" />
            ) : (
              <TrashIcon data-icon="inline-start" />
            )}
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function WorkspaceToolbar({
  breadcrumbFolders,
  onOpenFolder,
  pageSize,
  searchQuery,
  setPageSize,
  setSearchQuery,
  setSortDirection,
  setSortKey,
  share,
  sortDirection,
  sortKey,
}: ToolbarProps) {
  return (
    <div className="flex flex-col gap-5">
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
                          onClick={() => void onOpenFolder(folder.id)}
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

        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-4xl tracking-[-0.05em] text-foreground sm:text-5xl">
              File management
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">
              Browse folders and files together in one workspace table, then use
              right click for the actions that matter.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {share ? (
              <Badge variant="outline">{share.permission_level}</Badge>
            ) : null}
            <Badge variant={share ? "default" : "secondary"}>
              {share ? "Active share" : "No share"}
            </Badge>
          </div>
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
                onChange={(event) => setSearchQuery(event.target.value)}
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
              onValueChange={(value) => setSortKey(value as SortKey)}
              value={sortKey}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Sort field" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="name">Name</SelectItem>
                  <SelectItem value="updated_at">Updated</SelectItem>
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
    </div>
  );
}

function WorkspaceResults({
  contents,
  currentFolderId,
  onDeleteResource,
  onDownloadFile,
  onEditResource,
  onOpenFolder,
  resourceResults,
  searchQuery,
  workspacePending,
}: WorkspaceResultsProps) {
  if (workspacePending && !contents) {
    return (
      <div className="grid gap-3">
        <Skeleton className="h-28 rounded-2xl" />
        <Skeleton className="h-16 rounded-2xl" />
        <Skeleton className="h-16 rounded-2xl" />
      </div>
    );
  }

  if ((resourceResults?.pagination.total_items ?? 0) === 0) {
    return (
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
              : "Right click anywhere in the workspace to upload, create a folder, or manage sharing."}
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <div className="overflow-hidden rounded-[1.75rem] border border-border/70 bg-background/70 shadow-lg shadow-black/5 backdrop-blur">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Kind</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Updated</TableHead>
            <TableHead>Size</TableHead>
            <TableHead className="text-right">Quick action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {(resourceResults?.items ?? []).map((item) => (
            <WorkspaceRow
              item={item}
              key={item.item_type === "FOLDER" ? item.folder.id : item.file.id}
              onDelete={() =>
                onDeleteResource(
                  item.item_type === "FOLDER"
                    ? toFolderActionResource(item.folder)
                    : toFileActionResource(item.file, currentFolderId),
                )
              }
              onDownload={() =>
                item.item_type === "FILE"
                  ? void onDownloadFile(item.file.id, item.file.stored_filename)
                  : undefined
              }
              onMove={() =>
                onEditResource({
                  mode: "move",
                  resource:
                    item.item_type === "FOLDER"
                      ? toFolderActionResource(item.folder)
                      : toFileActionResource(item.file, currentFolderId),
                })
              }
              onOpenFolder={() =>
                item.item_type === "FOLDER"
                  ? void onOpenFolder(item.folder.id)
                  : undefined
              }
              onRename={() =>
                onEditResource({
                  mode: "rename",
                  resource:
                    item.item_type === "FOLDER"
                      ? toFolderActionResource(item.folder)
                      : toFileActionResource(item.file, currentFolderId),
                })
              }
            />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function WorkspaceRow({
  item,
  onDelete,
  onDownload,
  onMove,
  onOpenFolder,
  onRename,
}: WorkspaceRowProps) {
  const isFolder = item.item_type === "FOLDER";
  const name = isFolder ? item.folder.name : item.file.stored_filename;
  const updatedAt = isFolder ? item.folder.updated_at : item.file.updated_at;
  const size = isFolder ? "—" : formatBytes(item.file.size_bytes);
  const status = isFolder ? "—" : item.file.status;

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <TableRow className="cursor-default">
          <TableCell className="font-medium">
            {isFolder ? (
              <button
                className="flex items-center gap-3 text-left text-foreground"
                onClick={onOpenFolder}
                type="button"
              >
                <FolderIcon className="text-muted-foreground" />
                <span>{name}</span>
              </button>
            ) : (
              <div className="flex items-center gap-3">
                <FileTextIcon className="text-muted-foreground" />
                <span>{name}</span>
              </div>
            )}
          </TableCell>
          <TableCell>
            <Badge variant="outline">{isFolder ? "Folder" : "File"}</Badge>
          </TableCell>
          <TableCell>
            {status === "—" ? "—" : <Badge>{status}</Badge>}
          </TableCell>
          <TableCell>{formatDate(updatedAt)}</TableCell>
          <TableCell>{size}</TableCell>
          <TableCell className="text-right">
            {isFolder ? (
              <Button onClick={onOpenFolder} size="sm" variant="ghost">
                <FolderOpenIcon data-icon="inline-start" />
                Open
              </Button>
            ) : (
              <Button onClick={onDownload} size="sm" variant="ghost">
                <ArrowDownToLineIcon data-icon="inline-start" />
                Download
              </Button>
            )}
          </TableCell>
        </TableRow>
      </ContextMenuTrigger>
      <ContextMenuContent>
        {isFolder ? (
          <ContextMenuItem onClick={onOpenFolder}>
            <FolderOpenIcon />
            Open folder
          </ContextMenuItem>
        ) : (
          <ContextMenuItem onClick={onDownload}>
            <ArrowDownToLineIcon />
            Download file
          </ContextMenuItem>
        )}
        <ContextMenuItem onClick={onRename}>
          <PencilIcon />
          Rename
        </ContextMenuItem>
        <ContextMenuItem onClick={onMove}>
          <FolderInputIcon />
          Move
        </ContextMenuItem>
        <ContextMenuItem onClick={onDelete}>
          <TrashIcon />
          Delete
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

function toFolderActionResource(folder: Folder): ActionResource {
  return {
    kind: "folder",
    id: folder.id,
    name: folder.name,
    parentId: folder.parent_id,
    pathCache: folder.path_cache,
  };
}

function toFileActionResource(
  file: FileSummary,
  parentId: string,
): ActionResource {
  return {
    kind: "file",
    id: file.id,
    name: file.stored_filename,
    parentId,
  };
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
