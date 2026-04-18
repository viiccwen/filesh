import { z } from "zod";

export const folderSchema = z.object({
  id: z.string().uuid(),
  owner_id: z.string().uuid(),
  parent_id: z.string().uuid().nullable(),
  name: z.string(),
  path_cache: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const fileSummarySchema = z.object({
  id: z.string().uuid(),
  stored_filename: z.string(),
  content_type: z.string().nullable(),
  size_bytes: z.number(),
  status: z.enum(["PENDING", "ACTIVE", "FAILED", "DELETING"]),
  created_at: z.string(),
  updated_at: z.string(),
});

export const fileReadSchema = z.object({
  id: z.string().uuid(),
  owner_id: z.string().uuid(),
  folder_id: z.string().uuid(),
  original_filename: z.string(),
  stored_filename: z.string(),
  extension: z.string().nullable(),
  content_type: z.string().nullable(),
  size_bytes: z.number(),
  checksum_sha256: z.string().nullable(),
  object_key: z.string(),
  storage_bucket: z.string(),
  status: z.enum(["PENDING", "ACTIVE", "FAILED", "DELETING"]),
  uploaded_by: z.string().uuid(),
  version: z.number().int().nonnegative(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const folderContentsSchema = z.object({
  folder: folderSchema,
  folders: z.array(folderSchema),
  files: z.array(fileSummarySchema),
});

export const resourceSearchItemSchema = z.discriminatedUnion("item_type", [
  z.object({
    item_type: z.literal("FOLDER"),
    folder: folderSchema,
  }),
  z.object({
    item_type: z.literal("FILE"),
    file: fileSummarySchema,
  }),
]);

export const resourceSearchPaginationSchema = z.object({
  page: z.number().int().positive(),
  page_size: z.number().int().positive(),
  total_items: z.number().int().nonnegative(),
  total_pages: z.number().int().positive(),
});

export const resourceSearchResponseSchema = z.object({
  items: z.array(resourceSearchItemSchema),
  pagination: resourceSearchPaginationSchema,
});

export const shareSchema = z.object({
  id: z.string().uuid(),
  resource_type: z.enum(["FILE", "FOLDER"]),
  resource_id: z.string().uuid(),
  share_mode: z.enum(["GUEST", "USER_ONLY", "EMAIL_INVITATION"]),
  permission_level: z.enum(["VIEW_DOWNLOAD", "UPLOAD", "DELETE"]),
  expires_at: z.string().nullable(),
  is_revoked: z.boolean(),
  invitation_emails: z.array(z.email()),
  share_url: z.string(),
});

export const shareFormSchema = z.object({
  share_mode: z.enum(["GUEST", "USER_ONLY", "EMAIL_INVITATION"]),
  permission_level: z.enum(["VIEW_DOWNLOAD", "UPLOAD", "DELETE"]),
  expiry: z.enum(["hour", "day", "never"]),
  invitation_emails: z.array(z.email()).default([]),
});

export const shareAccessResponseSchema = z.object({
  resource_type: z.enum(["FILE", "FOLDER"]),
  share_mode: z.enum(["GUEST", "USER_ONLY", "EMAIL_INVITATION"]),
  permission_level: z.enum(["VIEW_DOWNLOAD", "UPLOAD", "DELETE"]),
  expires_at: z.string().nullable(),
  folder: folderSchema.nullable(),
  file: fileReadSchema.nullable(),
});

export const sharedFolderContentsResponseSchema = z.object({
  folder: folderSchema,
  folders: z.array(folderSchema),
  files: z.array(fileSummarySchema),
  permission_level: z.enum(["VIEW_DOWNLOAD", "UPLOAD", "DELETE"]),
});

export type Folder = z.infer<typeof folderSchema>;
export type FileSummary = z.infer<typeof fileSummarySchema>;
export type FileRead = z.infer<typeof fileReadSchema>;
export type FolderContents = z.infer<typeof folderContentsSchema>;
export type ResourceSearchItem = z.infer<typeof resourceSearchItemSchema>;
export type ResourceSearchResponse = z.infer<
  typeof resourceSearchResponseSchema
>;
export type Share = z.infer<typeof shareSchema>;
export type ShareFormValues = z.infer<typeof shareFormSchema>;
export type ShareAccessResponse = z.infer<typeof shareAccessResponseSchema>;
export type SharedFolderContentsResponse = z.infer<
  typeof sharedFolderContentsResponseSchema
>;
