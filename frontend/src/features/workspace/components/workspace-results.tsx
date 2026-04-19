import {
  ArrowDownToLineIcon,
  FileTextIcon,
  FolderIcon,
  FolderOpenIcon,
  PencilIcon,
  SearchIcon,
  TrashIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
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
import { formatBytes, formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Folder } from "@/features/workspace/schemas";

import type {
  ActionResource,
  WorkspaceResultsProps,
  WorkspaceRowProps,
} from "./workspace-screen.types";
import {
  toFileActionResource,
  toFolderActionResource,
} from "./workspace-screen.utils";

export function WorkspaceResults({
  contents,
  currentFolderId,
  onDeleteResources,
  onDownloadFile,
  onEditResource,
  onMoveResource,
  onOpenFolder,
  resourceResults,
  searchQuery,
  selectedResourceIds,
  setSelectedResourceIds,
  workspacePending,
}: WorkspaceResultsProps) {
  const [draggedResource, setDraggedResource] = useState<ActionResource | null>(
    null,
  );
  const [dropTargetId, setDropTargetId] = useState<string | null>(null);
  const [movePendingId, setMovePendingId] = useState<string | null>(null);
  const [selectionBox, setSelectionBox] = useState<{
    active: boolean;
    currentX: number;
    currentY: number;
    originX: number;
    originY: number;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const rowRefs = useRef(new Map<string, HTMLTableRowElement>());
  const marqueeSelectionRef = useRef(false);

  const resources = useMemo(
    () =>
      (resourceResults?.items ?? []).map((item) =>
        item.item_type === "FOLDER"
          ? toFolderActionResource(item.folder)
          : toFileActionResource({
              file: item.file,
              parentId: currentFolderId,
            }),
      ),
    [currentFolderId, resourceResults?.items],
  );

  const resourceMap = useMemo(
    () => new Map(resources.map((resource) => [resource.id, resource])),
    [resources],
  );

  const selectedResources = useMemo(
    () =>
      selectedResourceIds
        .map((resourceId) => resourceMap.get(resourceId))
        .filter(
          (resource): resource is ActionResource => resource !== undefined,
        ),
    [resourceMap, selectedResourceIds],
  );

  useEffect(() => {
    setSelectedResourceIds([]);
  }, [resourceResults?.items]);

  useEffect(() => {
    if (!selectionBox) {
      return;
    }

    const startBox = selectionBox;

    function handlePointerMove(event: PointerEvent) {
      const containerRect = containerRef.current?.getBoundingClientRect();
      if (!containerRect) {
        return;
      }

      const nextBox = updateSelectionBox(
        startBox,
        event.clientX - containerRect.left,
        event.clientY - containerRect.top,
      );
      setSelectionBox(nextBox);

      if (!nextBox.active) {
        return;
      }

      marqueeSelectionRef.current = true;
      setSelectedResourceIds(getSelectedResourceIds(nextBox));
    }

    function handlePointerUp() {
      setSelectionBox(null);
      window.setTimeout(() => {
        marqueeSelectionRef.current = false;
      }, 0);
    }

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp, { once: true });

    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [selectionBox]);

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
    <div
      className="relative overflow-hidden rounded-[1.75rem] border border-border/70 bg-background/70 shadow-lg shadow-black/5 backdrop-blur"
      ref={containerRef}
    >
      {selectionBox?.active ? (
        <div
          className="pointer-events-none absolute z-10 rounded-md border border-primary/50 bg-primary/12"
          style={getSelectionBoxStyle(selectionBox)}
        />
      ) : null}

      <div className="relative overflow-hidden rounded-[1.75rem] border border-border/70 bg-background/70 shadow-lg shadow-black/5 backdrop-blur">
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
            {(resourceResults?.items ?? []).map((item) => (
              <WorkspaceRow
                draggedResource={draggedResource}
                dropTargetId={dropTargetId}
                isMovePending={movePendingId !== null}
                isSelected={selectedResourceIds.includes(
                  item.item_type === "FOLDER" ? item.folder.id : item.file.id,
                )}
                item={item}
                key={
                  item.item_type === "FOLDER" ? item.folder.id : item.file.id
                }
                onDelete={() => {
                  const resource =
                    item.item_type === "FOLDER"
                      ? toFolderActionResource(item.folder)
                      : toFileActionResource({
                          file: item.file,
                          parentId: currentFolderId,
                        });
                  const resourcesToDelete =
                    selectedResourceIds.includes(resource.id) &&
                    selectedResources.length > 1
                      ? selectedResources
                      : [resource];
                  onDeleteResources(resourcesToDelete);
                }}
                onDownload={() =>
                  item.item_type === "FILE"
                    ? void onDownloadFile(
                        item.file.id,
                        item.file.stored_filename,
                      )
                    : undefined
                }
                onDragEnd={() => {
                  setDraggedResource(null);
                  setDropTargetId(null);
                }}
                onDragStart={() =>
                  setDraggedResource(
                    item.item_type === "FOLDER"
                      ? toFolderActionResource(item.folder)
                      : toFileActionResource({
                          file: item.file,
                          parentId: currentFolderId,
                        }),
                  )
                }
                onDropResource={(targetFolder) => {
                  void handleDropResource(targetFolder);
                }}
                onOpenFolder={() =>
                  item.item_type === "FOLDER" && !marqueeSelectionRef.current
                    ? void onOpenFolder(item.folder.id)
                    : undefined
                }
                onPointerDown={(event) => {
                  if (event.button !== 0) {
                    return;
                  }

                  const containerRect =
                    containerRef.current?.getBoundingClientRect();
                  if (!containerRect) {
                    return;
                  }

                  const originX = event.clientX - containerRect.left;
                  const originY = event.clientY - containerRect.top;

                  setSelectionBox({
                    active: false,
                    currentX: originX,
                    currentY: originY,
                    originX,
                    originY,
                  });
                }}
                onRename={() =>
                  onEditResource({
                    mode: "rename",
                    resource:
                      item.item_type === "FOLDER"
                        ? toFolderActionResource(item.folder)
                        : toFileActionResource({
                            file: item.file,
                            parentId: currentFolderId,
                          }),
                  })
                }
                rowRef={(node) => {
                  const resourceId =
                    item.item_type === "FOLDER" ? item.folder.id : item.file.id;

                  if (node) {
                    rowRefs.current.set(resourceId, node);
                  } else {
                    rowRefs.current.delete(resourceId);
                  }
                }}
                setDropTargetId={setDropTargetId}
              />
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );

  async function handleDropResource(targetFolder: Folder) {
    if (!draggedResource) {
      return;
    }

    if (!canDropResource(draggedResource, targetFolder)) {
      setDropTargetId(null);
      return;
    }

    setMovePendingId(draggedResource.id);
    setDropTargetId(null);

    try {
      await onMoveResource(draggedResource, targetFolder);
    } finally {
      setDraggedResource(null);
      setMovePendingId(null);
    }
  }

  function getSelectedResourceIds(box: NonNullable<typeof selectionBox>) {
    const containerRect = containerRef.current?.getBoundingClientRect();
    if (!containerRect) {
      return [];
    }

    const boxRect = normalizeSelectionBox(box);
    const nextSelectedIds: string[] = [];

    for (const [resourceId, rowNode] of rowRefs.current.entries()) {
      const rowRect = rowNode.getBoundingClientRect();
      const relativeRect = {
        bottom: rowRect.bottom - containerRect.top,
        left: rowRect.left - containerRect.left,
        right: rowRect.right - containerRect.left,
        top: rowRect.top - containerRect.top,
      };

      if (rectanglesIntersect(boxRect, relativeRect)) {
        nextSelectedIds.push(resourceId);
      }
    }

    return nextSelectedIds;
  }
}

function WorkspaceRow({
  draggedResource,
  dropTargetId,
  isMovePending,
  isSelected,
  item,
  onDelete,
  onDownload,
  onDragEnd,
  onDragStart,
  onDropResource,
  onOpenFolder,
  onPointerDown,
  onRename,
  rowRef,
  setDropTargetId,
}: WorkspaceRowProps) {
  const isFolder = item.item_type === "FOLDER";
  const name = isFolder ? item.folder.name : item.file.stored_filename;
  const updatedAt = isFolder ? item.folder.updated_at : item.file.updated_at;
  const size = isFolder ? "—" : formatBytes(item.file.size_bytes);
  const status = isFolder ? "—" : item.file.status;
  const folder = isFolder ? item.folder : null;
  const canAcceptDrop =
    folder && draggedResource
      ? canDropResource(draggedResource, folder)
      : false;

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <TableRow
          className={cn(
            isFolder
              ? "cursor-pointer transition-colors hover:bg-muted/20"
              : "cursor-default",
            isSelected && "bg-primary/10 ring-1 ring-primary/20",
            canAcceptDrop &&
              "data-[drop-target=true]:bg-primary/8 data-[drop-target=true]:ring-1 data-[drop-target=true]:ring-primary/20",
            isMovePending && "opacity-80",
          )}
          data-drop-target={
            canAcceptDrop && folder?.id === dropTargetId ? true : undefined
          }
          data-state={isSelected ? "selected" : undefined}
          draggable
          onDragEnd={onDragEnd}
          onDragEnter={() => {
            if (folder && canAcceptDrop) {
              setDropTargetId(folder.id);
            }
          }}
          onDragOver={(event) => {
            if (!folder || !canAcceptDrop) {
              return;
            }

            event.preventDefault();
            if (dropTargetId !== folder.id) {
              setDropTargetId(folder.id);
            }
          }}
          onDragLeave={() => {
            if (folder?.id === dropTargetId) {
              setDropTargetId(null);
            }
          }}
          onDragStart={(event) => {
            event.dataTransfer.effectAllowed = "move";
            onDragStart();
          }}
          onDrop={(event) => {
            if (!folder || !canAcceptDrop) {
              return;
            }

            event.preventDefault();
            onDropResource(folder);
          }}
          onPointerDown={onPointerDown}
          onClick={isFolder ? onOpenFolder : undefined}
          ref={rowRef}
        >
          <TableCell className="font-medium">
            {isFolder ? (
              <div className="flex items-center gap-3 text-foreground">
                <FolderIcon className="text-muted-foreground" />
                <span>{name}</span>
              </div>
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
        </TableRow>
      </ContextMenuTrigger>
      <ContextMenuContent>
        {isFolder ? null : (
          <ContextMenuItem onClick={onDownload}>
            <ArrowDownToLineIcon />
            Download file
          </ContextMenuItem>
        )}
        <ContextMenuItem onClick={onRename}>
          <PencilIcon />
          Rename
        </ContextMenuItem>
        <ContextMenuItem onClick={onDelete}>
          <TrashIcon />
          Delete
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

function updateSelectionBox(
  box: {
    active: boolean;
    currentX: number;
    currentY: number;
    originX: number;
    originY: number;
  },
  currentX: number,
  currentY: number,
) {
  return {
    ...box,
    active:
      box.active ||
      Math.abs(box.originX - currentX) > 4 ||
      Math.abs(box.originY - currentY) > 4,
    currentX,
    currentY,
  };
}

function normalizeSelectionBox(box: {
  currentX: number;
  currentY: number;
  originX: number;
  originY: number;
}) {
  return {
    bottom: Math.max(box.originY, box.currentY),
    left: Math.min(box.originX, box.currentX),
    right: Math.max(box.originX, box.currentX),
    top: Math.min(box.originY, box.currentY),
  };
}

function getSelectionBoxStyle(box: {
  currentX: number;
  currentY: number;
  originX: number;
  originY: number;
}) {
  const normalized = normalizeSelectionBox(box);

  return {
    height: `${normalized.bottom - normalized.top}px`,
    left: `${normalized.left}px`,
    top: `${normalized.top}px`,
    width: `${normalized.right - normalized.left}px`,
  };
}

function rectanglesIntersect(
  left: { bottom: number; left: number; right: number; top: number },
  right: { bottom: number; left: number; right: number; top: number },
) {
  return !(
    left.right < right.left ||
    left.left > right.right ||
    left.bottom < right.top ||
    left.top > right.bottom
  );
}

function canDropResource(
  resource: ActionResource,
  targetFolder: Folder,
): boolean {
  if (resource.kind === "file") {
    return resource.parentId !== targetFolder.id;
  }

  if (resource.id === targetFolder.id) {
    return false;
  }

  if (!resource.pathCache || !targetFolder.path_cache) {
    return true;
  }

  return (
    targetFolder.path_cache !== resource.pathCache &&
    !targetFolder.path_cache.startsWith(`${resource.pathCache}/`)
  );
}
