# Frontend

This package contains the FileSh web client built with React 19, TypeScript, Vite, Tailwind CSS v4, and shadcn/ui components.

## Features

- Landing, login, and registration flows
- Authenticated workspace view at `/app`
- File and folder browsing with search, sorting, pagination, and context actions
- Upload, download, rename, move, and delete interactions
- Share management UI for files and folders
- Shared-link access page at `/s/:token`
- Status pages for expired, unauthorized, deleted, and not-found states

## Tech Stack

- React 19
- TypeScript
- Vite
- React Router 7
- Zustand for client auth state
- Zod for request/response validation
- Tailwind CSS v4
- shadcn/ui and Radix primitives
- Sonner for toast notifications

## Project Structure

```text
frontend/
|-- src/
|   |-- app/                  App shell and router
|   |-- components/           Shared UI and navigation components
|   |-- features/auth/        Auth forms, schemas, and Zustand store
|   |-- features/workspace/   Workspace views, dialogs, and helpers
|   |-- lib/                  API client, formatters, shared types
|   `-- pages/                Route-level page components
|-- package.json
|-- vite.config.ts
`-- components.json
```

## Routes

- `/`: landing page
- `/login`: guest-only login screen
- `/register`: guest-only registration screen
- `/app`: authenticated workspace
- `/s/:token`: shared file/folder access
- `/expired`, `/unauthorized`, `/not-found`, `/deleted`: state pages

## API Integration

The client talks to the backend through `src/lib/api.ts`.

- Base URL: `VITE_API_BASE_URL`
- Access tokens are sent as `Authorization: Bearer ...`
- Refresh sessions use HTTP-only cookies
- Runtime response payloads are validated with Zod

## Environment

Create a `.env` in the repository root, or provide the variable through your shell:

```env
VITE_API_BASE_URL=http://localhost:8000
```

When running through `docker compose`, this value comes from the root `.env`.

## Run Locally

```bash
cd frontend
pnpm install
pnpm dev --host 0.0.0.0 --port 5173
```

Open `http://localhost:5173`.

## Scripts

```bash
pnpm dev
pnpm build
pnpm preview
pnpm lint
pnpm format
```

Notes:

- `pnpm lint` currently performs a TypeScript no-emit check.
- `pnpm format` runs `prettier --check .`.

## UI Notes

- Shared UI primitives live under `src/components/ui`.
- Router-level lazy loading is configured in `src/app/router.tsx`.
- Auth bootstrap happens through `src/features/auth/store.ts`, which attempts a refresh-token session on app start.
