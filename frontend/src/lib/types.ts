export type UserRead = {
  id: string;
  email: string;
  username: string;
  nickname: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AccessTokenResponse = {
  access_token: string;
  token_type: "bearer";
  user: UserRead;
};

export type FolderRead = {
  id: string;
  owner_id: string;
  parent_id: string | null;
  name: string;
  path_cache: string | null;
  created_at: string;
  updated_at: string;
};

export type FileSummary = {
  id: string;
  stored_filename: string;
  content_type: string | null;
  size_bytes: number;
  status: "PENDING" | "ACTIVE" | "FAILED" | "DELETING";
};

export type FolderContentsResponse = {
  folder: FolderRead;
  folders: FolderRead[];
  files: FileSummary[];
};

export type ShareRead = {
  id: string;
  resource_type: "FILE" | "FOLDER";
  resource_id: string;
  share_mode: "GUEST" | "USER_ONLY" | "EMAIL_INVITATION";
  permission_level: "VIEW_DOWNLOAD" | "UPLOAD" | "DELETE";
  expires_at: string | null;
  is_revoked: boolean;
  invitation_emails: string[];
  share_url: string;
};

export type RegisterPayload = {
  email: string;
  username: string;
  nickname: string;
  password: string;
};

export type LoginPayload = {
  identifier: string;
  password: string;
};
