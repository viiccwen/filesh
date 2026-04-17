import { z } from "zod";

export const userSchema = z.object({
  id: z.string().uuid(),
  email: z.email(),
  username: z.string(),
  nickname: z.string(),
  is_active: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const accessTokenResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.literal("bearer"),
  user: userSchema,
});

export const loginFormSchema = z.object({
  identifier: z.string().trim().min(1, "Enter an email or username"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

export const registerFormSchema = z.object({
  email: z.email("Enter a valid email address"),
  username: z.string().trim().min(3, "Username must be at least 3 characters"),
  nickname: z.string().trim().min(1, "Enter a nickname"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

export type User = z.infer<typeof userSchema>;
export type AccessTokenResponse = z.infer<typeof accessTokenResponseSchema>;
export type LoginFormValues = z.infer<typeof loginFormSchema>;
export type RegisterFormValues = z.infer<typeof registerFormSchema>;
