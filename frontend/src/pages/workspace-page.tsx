import { WorkspaceScreen } from "@/features/workspace/components/workspace-screen";

export function WorkspacePage() {
  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <WorkspaceScreen />
      </div>
    </div>
  );
}
