import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { FolderInputIcon, Link2Icon, UploadIcon } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { useAuthStore } from "@/features/auth/store";
import {
  DeleteResourceDialog,
  WorkspaceActionDialog,
} from "@/features/workspace/components/workspace-action-dialogs";
import { WorkspaceNavbar } from "@/features/workspace/components/workspace-navbar";
import { WorkspaceResults } from "@/features/workspace/components/workspace-results";
import { ShareManagementSheet } from "@/features/workspace/components/share-management-sheet";
import {
  WorkspacePagination,
  WorkspaceToolbar,
} from "@/features/workspace/components/workspace-toolbar";
import {
  shareFormSchema,
  type Folder,
  type FolderContents,
  type ResourceSearchResponse,
  type Share,
  type ShareFormValues,
} from "@/features/workspace/schemas";
import type {
  ActionResource,
  EditDialogState,
  SortKey,
} from "@/features/workspace/components/workspace-screen.types";
import {
  getErrorMessage,
  toAbsoluteUrl,
} from "@/features/workspace/components/workspace-screen.utils";
import {
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

  async function handleMoveResource(
    resource: ActionResource,
    targetFolder: Folder,
  ) {
    if (!contents) {
      return;
    }

    try {
      if (resource.kind === "folder") {
        await moveFolder(authToken, resource.id, {
          target_parent_id: targetFolder.id,
        });
        toast.success("Folder moved");
      } else {
        await moveFile(authToken, resource.id, {
          target_folder_id: targetFolder.id,
        });
        toast.success("File moved");
      }

      await loadWorkspace(authToken, contents.folder.id);
    } catch (error) {
      toast.error(getErrorMessage(error));
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
        <WorkspaceNavbar onLogout={logout} user={user} />

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
                onMoveResource={handleMoveResource}
                onOpenFolder={openFolder}
                resourceResults={resourceResults}
                searchQuery={searchQuery}
                workspacePending={workspacePending}
              />

              <WorkspacePagination
                pageIndex={pageIndex}
                pageSize={pageSize}
                pending={resourcePending}
                setPageIndex={setPageIndex}
                totalItems={resourceResults?.pagination.total_items ?? 0}
                totalPages={resourceResults?.pagination.total_pages ?? 1}
              />
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
