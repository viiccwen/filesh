import type {
  FileSummary,
  Folder,
  FolderContents,
  ResourceSearchItem,
  ResourceSearchResponse,
  Share,
} from "@/features/workspace/schemas";

export type SortKey = "name" | "updated_at" | "size" | "type";

export type ActionResource =
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

export type EditDialogState =
  | { mode: "create-folder"; parentId: string }
  | { mode: "rename"; resource: ActionResource }
  | { mode: "move"; resource: ActionResource }
  | null;

export type ToolbarProps = {
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

export type WorkspaceResultsProps = {
  contents: FolderContents | null;
  currentFolderId: string;
  onDeleteResource: (resource: ActionResource) => void;
  onDownloadFile: (fileId: string, filename: string) => Promise<void>;
  onEditResource: (state: EditDialogState) => void;
  onMoveResource: (
    resource: ActionResource,
    targetFolder: Folder,
  ) => Promise<void>;
  onOpenFolder: (folderId: string) => Promise<void>;
  resourceResults: ResourceSearchResponse | null;
  searchQuery: string;
  workspacePending: boolean;
};

export type WorkspaceRowProps = {
  draggedResource: ActionResource | null;
  dropTargetId: string | null;
  isMovePending: boolean;
  item: ResourceSearchItem;
  onDelete: () => void;
  onDownload: () => void;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDropResource: (targetFolder: Folder) => void;
  onOpenFolder: () => void;
  onRename: () => void;
  setDropTargetId: (folderId: string | null) => void;
};

export type WorkspaceActionDialogProps = {
  actionPending: boolean;
  editDialogState: EditDialogState;
  moveTargetId: string;
  moveTargets: Folder[];
  onOpenChange: (state: EditDialogState) => void;
  onSave: () => void;
  resourceName: string;
  setMoveTargetId: (value: string) => void;
  setResourceName: (value: string) => void;
};

export type DeleteResourceDialogProps = {
  actionPending: boolean;
  deleteDialogResource: ActionResource | null;
  onConfirm: () => void;
  onOpenChange: (resource: ActionResource | null) => void;
};

export type WorkspaceNavbarProps = {
  onLogout: () => Promise<void>;
  user: {
    nickname: string;
    username: string;
  };
};

export type WorkspacePaginationProps = {
  pageIndex: number;
  pageSize: number;
  pending: boolean;
  setPageIndex: React.Dispatch<React.SetStateAction<number>>;
  totalItems: number;
  totalPages: number;
};

export type FileActionInput = {
  file: FileSummary;
  parentId: string;
};
