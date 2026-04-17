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
  shareSchema,
  type Folder,
  type FolderContents,
  type Share,
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
): Promise<void> {
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

  await request("/api/files/upload/finalize", {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      upload_session_id: initResponse.session_id,
      size_bytes: file.size,
    }),
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
  return request<Share>(`/api/folders/${folderId}/share`, {
    method: "POST",
    accessToken,
    body: JSON.stringify({
      share_mode: "GUEST",
      permission_level: "VIEW_DOWNLOAD",
      expiry: "never",
      invitation_emails: [],
    }),
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
