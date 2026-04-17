import { ApiError } from "@/lib/api";

import type { ActionResource, FileActionInput } from "./workspace-screen.types";

export const PAGE_SIZE_OPTIONS = ["8", "16", "24"];

export function toFolderActionResource(folder: {
  id: string;
  name: string;
  parent_id: string | null;
  path_cache: string | null;
}): ActionResource {
  return {
    kind: "folder",
    id: folder.id,
    name: folder.name,
    parentId: folder.parent_id,
    pathCache: folder.path_cache,
  };
}

export function toFileActionResource({
  file,
  parentId,
}: FileActionInput): ActionResource {
  return {
    kind: "file",
    id: file.id,
    name: file.stored_filename,
    parentId,
  };
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected error";
}

export function toAbsoluteUrl(pathname: string): string {
  return new URL(pathname, window.location.origin).toString();
}
