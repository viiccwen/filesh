import {
  accessTokenResponseSchema,
  type AccessTokenResponse,
  type LoginFormValues,
  type RegisterFormValues,
  userSchema,
  type User,
} from "@/features/auth/schemas";
import {
  folderContentsSchema,
  folderSchema,
  fileReadSchema,
  resourceSearchResponseSchema,
  shareFormSchema,
  shareAccessResponseSchema,
  shareSchema,
  sharedFolderContentsResponseSchema,
  type Folder,
  type FolderContents,
  type FileRead,
  type ResourceSearchResponse,
  type ShareFormValues,
  type Share,
  type ShareAccessResponse,
  type SharedFolderContentsResponse,
} from "@/features/workspace/schemas";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type RequestOptions<T> = RequestInit & {
  accessToken?: string | null;
  parse?: (value: unknown) => T;
  responseType?: "json" | "blob" | "void";
};

async function request<T>(
  path: string,
  options: RequestOptions<T> = {},
): Promise<T> {
  const {
    accessToken,
    parse,
    responseType = "json",
    headers,
    body,
    ...init
  } = options;
  const requestHeaders = new Headers(headers);

  if (accessToken) {
    requestHeaders.set("Authorization", `Bearer ${accessToken}`);
  }

  if (
    body &&
    !(body instanceof FormData) &&
    !requestHeaders.has("Content-Type")
  ) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    body,
    headers: requestHeaders,
    credentials: "include",
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;

    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? detail;
    } catch {
      detail = response.statusText || detail;
    }

    throw new ApiError(response.status, detail);
  }

  if (responseType === "void") {
    return undefined as T;
  }

  if (responseType === "blob") {
    return (await response.blob()) as T;
  }

  const payload = await response.json();
  return parse ? parse(payload) : (payload as T);
}

export function register(payload: RegisterFormValues): Promise<User> {
  return request<User>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
    parse: (value) => userSchema.parse(value),
  });
}

export function login(payload: LoginFormValues): Promise<AccessTokenResponse> {
  return request<AccessTokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
    parse: (value) => accessTokenResponseSchema.parse(value),
  });
}

export function refreshSession(): Promise<AccessTokenResponse> {
  return request<AccessTokenResponse>("/api/auth/refresh", {
    method: "POST",
    parse: (value) => accessTokenResponseSchema.parse(value),
  });
}

export function logout(): Promise<{ message: string }> {
  return request<{ message: string }>("/api/auth/logout", {
    method: "POST",
  });
}

export function getRootFolder(accessToken: string): Promise<Folder> {
  return request<Folder>("/api/folders/root", {
    accessToken,
    parse: (value) => folderSchema.parse(value),
  });
}

export function getFolderContents(
  folderId: string,
  accessToken: string,
): Promise<FolderContents> {
  return request<FolderContents>(`/api/folders/${folderId}/contents`, {
    accessToken,
    parse: (value) => folderContentsSchema.parse(value),
  });
}

export function searchResources(
  accessToken: string,
  params: {
    parent_id: string;
    q?: string;
    type?: "FILE" | "FOLDER";
    sort_by?: "name" | "updated_at" | "size" | "type";
    order?: "asc" | "desc";
    page?: number;
    page_size?: number;
  },
): Promise<ResourceSearchResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("parent_id", params.parent_id);

  if (params.q) {
    searchParams.set("q", params.q);
  }

  if (params.type) {
    searchParams.set("type", params.type);
  }

  if (params.sort_by) {
    searchParams.set("sort_by", params.sort_by);
  }

  if (params.order) {
    searchParams.set("order", params.order);
  }

  if (params.page) {
    searchParams.set("page", String(params.page));
  }

  if (params.page_size) {
    searchParams.set("page_size", String(params.page_size));
  }

  return request<ResourceSearchResponse>(
    `/api/resources/search?${searchParams.toString()}`,
    {
      accessToken,
      parse: (value) => resourceSearchResponseSchema.parse(value),
    },
  );
}

export function createFolder(
  accessToken: string,
  payload: { name: string; parent_id?: string | null },
): Promise<Folder> {
  return request<Folder>("/api/folders", {
    method: "POST",
    accessToken,
    body: JSON.stringify(payload),
    parse: (value) => folderSchema.parse(value),
  });
}

export async function uploadFile(
  accessToken: string,
  folderId: string,
  file: File,
): Promise<FileRead> {
  const initResponse = await request<{ session_id: string }>(
    "/api/files/upload/init",
    {
      method: "POST",
      accessToken,
      body: JSON.stringify({
        folder_id: folderId,
        filename: file.name,
        content_type: file.type || null,
        expected_size: file.size,
      }),
    },
  );

  const formData = new FormData();
  formData.set("file", file);

  await request<void>(`/api/files/upload/${initResponse.session_id}/content`, {
    method: "POST",
    accessToken,
    body: formData,
    responseType: "void",
  });

  return request<FileRead>("/api/files/upload/finalize", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      upload_session_id: initResponse.session_id,
      size_bytes: file.size,
    }),
    parse: (value) => fileReadSchema.parse(value),
  });
}

export async function downloadFile(
  accessToken: string,
  fileId: string,
): Promise<Blob> {
  return request<Blob>(`/api/files/${fileId}/download`, {
    accessToken,
    responseType: "blob",
  });
}

export function renameFolder(
  accessToken: string,
  folderId: string,
  payload: { name: string },
): Promise<void> {
  return request<void>(`/api/folders/${folderId}`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify(payload),
    responseType: "void",
  });
}

export function moveFolder(
  accessToken: string,
  folderId: string,
  payload: { target_parent_id: string },
): Promise<void> {
  return request<void>(`/api/folders/${folderId}/move`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify(payload),
    responseType: "void",
  });
}

export function deleteFolder(
  accessToken: string,
  folderId: string,
): Promise<void> {
  return request<void>(`/api/folders/${folderId}`, {
    method: "DELETE",
    accessToken,
    responseType: "void",
  });
}

export function renameFile(
  accessToken: string,
  fileId: string,
  payload: { filename: string },
): Promise<void> {
  return request<void>(`/api/files/${fileId}`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify(payload),
    responseType: "void",
  });
}

export function moveFile(
  accessToken: string,
  fileId: string,
  payload: { target_folder_id: string },
): Promise<void> {
  return request<void>(`/api/files/${fileId}/move`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify(payload),
    responseType: "void",
  });
}

export function deleteFile(accessToken: string, fileId: string): Promise<void> {
  return request<void>(`/api/files/${fileId}`, {
    method: "DELETE",
    accessToken,
    responseType: "void",
  });
}

export async function getFolderShare(
  accessToken: string,
  folderId: string,
): Promise<Share | null> {
  try {
    return await request<Share>(`/api/folders/${folderId}/share`, {
      accessToken,
      parse: (value) => shareSchema.parse(value),
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }

    throw error;
  }
}

export function createGuestFolderShare(
  accessToken: string,
  folderId: string,
): Promise<Share> {
  return updateFolderShare(accessToken, folderId, {
    share_mode: "GUEST",
    permission_level: "VIEW_DOWNLOAD",
    expiry: "never",
    invitation_emails: [],
  });
}

export function updateFolderShare(
  accessToken: string,
  folderId: string,
  payload: ShareFormValues,
): Promise<Share> {
  const normalizedPayload = shareFormSchema.parse(payload);

  return request<Share>(`/api/folders/${folderId}/share`, {
    method: "PATCH",
    accessToken,
    body: JSON.stringify(normalizedPayload),
    parse: (value) => shareSchema.parse(value),
  });
}

export function createFolderShare(
  accessToken: string,
  folderId: string,
  payload: ShareFormValues,
): Promise<Share> {
  const normalizedPayload = shareFormSchema.parse(payload);

  return request<Share>(`/api/folders/${folderId}/share`, {
    method: "POST",
    accessToken,
    body: JSON.stringify(normalizedPayload),
    parse: (value) => shareSchema.parse(value),
  });
}

export function revokeFolderShare(
  accessToken: string,
  folderId: string,
): Promise<void> {
  return request<void>(`/api/folders/${folderId}/share`, {
    method: "DELETE",
    accessToken,
    responseType: "void",
  });
}

export function getShareAccess(
  token: string,
  accessToken?: string | null,
): Promise<ShareAccessResponse> {
  return request<ShareAccessResponse>(`/s/${token}`, {
    accessToken,
    parse: (value) => shareAccessResponseSchema.parse(value),
  });
}

export function getSharedFolderContents(
  token: string,
  accessToken?: string | null,
  folderId?: string,
): Promise<SharedFolderContentsResponse> {
  const path = folderId
    ? `/s/${token}/folders/${folderId}/contents`
    : `/s/${token}/contents`;

  return request<SharedFolderContentsResponse>(path, {
    accessToken,
    parse: (value) => sharedFolderContentsResponseSchema.parse(value),
  });
}

export function getSharedFileMetadata(
  token: string,
  fileId: string,
  accessToken?: string | null,
): Promise<FileRead> {
  return request<FileRead>(`/s/${token}/files/${fileId}`, {
    accessToken,
    parse: (value) => fileReadSchema.parse(value),
  });
}

export function downloadSharedFile(
  token: string,
  accessToken?: string | null,
): Promise<Blob> {
  return request<Blob>(`/s/${token}/download`, {
    accessToken,
    responseType: "blob",
  });
}

export function downloadSharedFolderFile(
  token: string,
  fileId: string,
  accessToken?: string | null,
): Promise<Blob> {
  return request<Blob>(`/s/${token}/files/${fileId}/download`, {
    accessToken,
    responseType: "blob",
  });
}

export function createSharedFolder(
  token: string,
  payload: { name: string; parent_id?: string | null },
  accessToken?: string | null,
): Promise<Folder> {
  return request<Folder>(`/s/${token}/folders`, {
    method: "POST",
    accessToken,
    body: JSON.stringify(payload),
    parse: (value) => folderSchema.parse(value),
  });
}

export function deleteSharedFolder(
  token: string,
  folderId: string,
  accessToken?: string | null,
): Promise<void> {
  return request<void>(`/s/${token}/folders/${folderId}`, {
    method: "DELETE",
    accessToken,
    responseType: "void",
  });
}

export function deleteSharedFile(
  token: string,
  fileId: string,
  accessToken?: string | null,
): Promise<void> {
  return request<void>(`/s/${token}/files/${fileId}`, {
    method: "DELETE",
    accessToken,
    responseType: "void",
  });
}

export function uploadSharedFile(
  token: string,
  file: File,
  folderId?: string,
  accessToken?: string | null,
): Promise<FileRead> {
  const formData = new FormData();
  formData.set("file", file);

  if (folderId) {
    formData.set("folder_id", folderId);
  }

  return request<FileRead>(`/s/${token}/files`, {
    method: "POST",
    accessToken,
    body: formData,
    parse: (value) => fileReadSchema.parse(value),
  });
}
