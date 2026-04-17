import {
  ArrowDownToLineIcon,
  FileTextIcon,
  FolderIcon,
  FolderInputIcon,
  FolderOpenIcon,
  PencilIcon,
  SearchIcon,
  TrashIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

import type {
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
                    : toFileActionResource({
                        file: item.file,
                        parentId: currentFolderId,
                      }),
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
                      : toFileActionResource({
                          file: item.file,
                          parentId: currentFolderId,
                        }),
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
                      : toFileActionResource({
                          file: item.file,
                          parentId: currentFolderId,
                        }),
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
