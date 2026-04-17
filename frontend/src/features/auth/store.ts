import { create } from "zustand";

import {
  ApiError,
  login as loginRequest,
  logout as logoutRequest,
  refreshSession,
  register as registerRequest,
} from "@/lib/api";
import {
  loginFormSchema,
  registerFormSchema,
  type LoginFormValues,
  type RegisterFormValues,
  type User,
} from "@/features/auth/schemas";

type AuthStatus = "booting" | "guest" | "authenticated";

type AuthState = {
  accessToken: string | null;
  error: string | null;
  status: AuthStatus;
  user: User | null;
  bootstrap: () => Promise<void>;
  clearError: () => void;
  login: (values: LoginFormValues) => Promise<boolean>;
  logout: () => Promise<void>;
  register: (values: RegisterFormValues) => Promise<boolean>;
};

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  error: null,
  status: "booting",
  user: null,
  async bootstrap() {
    try {
      const response = await refreshSession();
      set({
        accessToken: response.access_token,
        error: null,
        status: "authenticated",
        user: response.user,
      });
    } catch {
      set({
        accessToken: null,
        error: null,
        status: "guest",
        user: null,
      });
    }
  },
  clearError() {
    set({ error: null });
  },
  async login(values) {
    const parsed = loginFormSchema.safeParse(values);
    if (!parsed.success) {
      set({ error: parsed.error.issues[0]?.message ?? "Invalid login input" });
      return false;
    }

    try {
      const response = await loginRequest(parsed.data);
      set({
        accessToken: response.access_token,
        error: null,
        status: "authenticated",
        user: response.user,
      });
      return true;
    } catch (error) {
      set({ error: getErrorMessage(error) });
      return false;
    }
  },
  async logout() {
    try {
      await logoutRequest();
    } finally {
      set({
        accessToken: null,
        error: null,
        status: "guest",
        user: null,
      });
    }
  },
  async register(values) {
    const parsed = registerFormSchema.safeParse(values);
    if (!parsed.success) {
      set({
        error: parsed.error.issues[0]?.message ?? "Invalid registration input",
      });
      return false;
    }

    try {
      await registerRequest(parsed.data);
      const response = await loginRequest({
        identifier: parsed.data.email,
        password: parsed.data.password,
      });
      set({
        accessToken: response.access_token,
        error: null,
        status: "authenticated",
        user: response.user,
      });
      return true;
    } catch (error) {
      set({ error: getErrorMessage(error) });
      return false;
    }
  },
}));

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected error";
}
