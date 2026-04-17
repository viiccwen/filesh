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

export const folderContentsSchema = z.object({
  folder: folderSchema,
  folders: z.array(folderSchema),
  files: z.array(fileSummarySchema),
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

export type Folder = z.infer<typeof folderSchema>;
export type FileSummary = z.infer<typeof fileSummarySchema>;
export type FolderContents = z.infer<typeof folderContentsSchema>;
export type Share = z.infer<typeof shareSchema>;
export type ShareFormValues = z.infer<typeof shareFormSchema>;
