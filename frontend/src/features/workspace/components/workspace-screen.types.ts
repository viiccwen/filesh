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
  onClearSelection: () => void;
  onDeleteSelection: () => void;
  onOpenFolder: (folderId: string) => Promise<void>;
  pageSize: number;
  searchQuery: string;
  selectedCount: number;
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
  onDeleteResources: (resources: ActionResource[]) => void;
  onDownloadFile: (fileId: string, filename: string) => Promise<void>;
  onEditResource: (state: EditDialogState) => void;
  onMoveResource: (
    resource: ActionResource,
    targetFolder: Folder,
  ) => Promise<void>;
  onOpenFolder: (folderId: string) => Promise<void>;
  resourceResults: ResourceSearchResponse | null;
  searchQuery: string;
  selectedResourceIds: string[];
  setSelectedResourceIds: React.Dispatch<React.SetStateAction<string[]>>;
  workspacePending: boolean;
};

export type WorkspaceRowProps = {
  draggedResource: ActionResource | null;
  dropTargetId: string | null;
  isMovePending: boolean;
  isSelected: boolean;
  item: ResourceSearchItem;
  onDelete: () => void;
  onDownload: () => void;
  onDragStart: () => void;
  onDragEnd: () => void;
  onDropResource: (targetFolder: Folder) => void;
  onOpenFolder: () => void;
  onPointerDown: (event: React.PointerEvent<HTMLTableRowElement>) => void;
  onRename: () => void;
  rowRef: (node: HTMLTableRowElement | null) => void;
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
  deleteDialogResources: ActionResource[];
  onConfirm: () => void;
  onOpenChange: (resources: ActionResource[]) => void;
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
