import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2Icon } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldContent,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  loginFormSchema,
  registerFormSchema,
  type LoginFormValues,
  type RegisterFormValues,
} from "@/features/auth/schemas";
import { useAuthStore } from "@/features/auth/store";

const defaultLoginValues: LoginFormValues = {
  identifier: "",
  password: "",
};

const defaultRegisterValues: RegisterFormValues = {
  email: "",
  username: "",
  nickname: "",
  password: "",
};

export function LoginCard() {
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [values, setValues] = useState<LoginFormValues>(defaultLoginValues);
  const authError = useAuthStore((state) => state.error);
  const clearError = useAuthStore((state) => state.clearError);
  const login = useAuthStore((state) => state.login);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearError();
    setPending(true);

    const parsed = loginFormSchema.safeParse(values);
    if (!parsed.success) {
      setPending(false);
      return;
    }

    const ok = await login(parsed.data);
    setPending(false);

    if (ok) {
      toast.success("Signed in successfully");
      navigate("/app");
    }
  }

  return (
    <AuthCardFrame description="" title="">
      <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="login-identifier">
              Email or username
            </FieldLabel>
            <Input
              id="login-identifier"
              value={values.identifier}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  identifier: event.target.value,
                }))
              }
              required
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="login-password">Password</FieldLabel>
            <FieldContent>
              <Input
                id="login-password"
                type="password"
                value={values.password}
                onChange={(event) =>
                  setValues((current) => ({
                    ...current,
                    password: event.target.value,
                  }))
                }
                required
              />
              <FieldDescription>
                Password must be at least 6 characters based on the current
                backend constraint.
              </FieldDescription>
            </FieldContent>
          </Field>
        </FieldGroup>
        {authError ? (
          <Alert variant="destructive">
            <AlertTitle>Sign-in failed</AlertTitle>
            <AlertDescription>{authError}</AlertDescription>
          </Alert>
        ) : null}
        <Button disabled={pending} type="submit">
          {pending ? (
            <Loader2Icon className="animate-spin" data-icon="inline-start" />
          ) : null}
          Open workspace
        </Button>
      </form>
    </AuthCardFrame>
  );
}

export function RegisterCard() {
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [values, setValues] = useState<RegisterFormValues>(
    defaultRegisterValues,
  );
  const authError = useAuthStore((state) => state.error);
  const clearError = useAuthStore((state) => state.clearError);
  const register = useAuthStore((state) => state.register);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    clearError();
    setPending(true);

    const parsed = registerFormSchema.safeParse(values);
    if (!parsed.success) {
      setPending(false);
      return;
    }

    const ok = await register(parsed.data);
    setPending(false);

    if (ok) {
      toast.success("Account created");
      navigate("/app");
    }
  }

  return (
    <AuthCardFrame
      description="This is a dedicated Register page from the spec instead of a tab embedded in the landing page."
      title="Register"
    >
      <form className="flex flex-col gap-6" onSubmit={handleSubmit}>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="register-email">Email</FieldLabel>
            <Input
              id="register-email"
              type="email"
              value={values.email}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  email: event.target.value,
                }))
              }
              required
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="register-username">Username</FieldLabel>
            <Input
              id="register-username"
              value={values.username}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  username: event.target.value,
                }))
              }
              required
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="register-nickname">Nickname</FieldLabel>
            <Input
              id="register-nickname"
              value={values.nickname}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  nickname: event.target.value,
                }))
              }
              required
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="register-password">Password</FieldLabel>
            <Input
              id="register-password"
              type="password"
              value={values.password}
              onChange={(event) =>
                setValues((current) => ({
                  ...current,
                  password: event.target.value,
                }))
              }
              required
            />
          </Field>
        </FieldGroup>
        {authError ? (
          <Alert variant="destructive">
            <AlertTitle>Registration failed</AlertTitle>
            <AlertDescription>{authError}</AlertDescription>
          </Alert>
        ) : null}
        <Button disabled={pending} type="submit">
          {pending ? (
            <Loader2Icon className="animate-spin" data-icon="inline-start" />
          ) : null}
          Create account
        </Button>
      </form>
    </AuthCardFrame>
  );
}

function AuthCardFrame({
  children,
  description,
  title,
}: {
  children: React.ReactNode;
  description: string;
  title: string;
}) {
  const showHeader = Boolean(title || description);

  return (
    <Card className="w-full rounded-[2.25rem] border-border/70 bg-background/82 shadow-xl shadow-black/5 ring-1 ring-white/50 backdrop-blur-xl">
      {showHeader ? (
        <CardHeader className="items-center text-center">
          {title ? <CardTitle>{title}</CardTitle> : null}
          {description ? (
            <CardDescription className="max-w-sm">
              {description}
            </CardDescription>
          ) : null}
        </CardHeader>
      ) : null}
      <CardContent>{children}</CardContent>
    </Card>
  );
}
