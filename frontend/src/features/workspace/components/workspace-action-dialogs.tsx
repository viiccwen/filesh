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
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  ArrowRightLeftIcon,
  FolderInputIcon,
  Loader2Icon,
  PencilIcon,
  TrashIcon,
} from "lucide-react";

import type {
  DeleteResourceDialogProps,
  WorkspaceActionDialogProps,
} from "./workspace-screen.types";

export function WorkspaceActionDialog({
  actionPending,
  editDialogState,
  moveTargetId,
  moveTargets,
  onOpenChange,
  onSave,
  resourceName,
  setMoveTargetId,
  setResourceName,
}: WorkspaceActionDialogProps) {
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

export function DeleteResourceDialog({
  actionPending,
  deleteDialogResource,
  onConfirm,
  onOpenChange,
}: DeleteResourceDialogProps) {
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
            <span>Delete</span>
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
