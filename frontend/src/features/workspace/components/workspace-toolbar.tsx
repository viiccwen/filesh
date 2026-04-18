import { Fragment } from "react";
import { SearchIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import {
  Field,
  FieldContent,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";

import type {
  SortKey,
  ToolbarProps,
  WorkspacePaginationProps,
} from "./workspace-screen.types";
import { PAGE_SIZE_OPTIONS } from "./workspace-screen.utils";

export function WorkspaceToolbar({
  breadcrumbFolders,
  onOpenFolder,
  pageSize,
  searchQuery,
  setPageSize,
  setSearchQuery,
  setSortDirection,
  setSortKey,
  share,
  sortDirection,
  sortKey,
}: ToolbarProps) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex min-w-0 flex-col gap-3">
        <Breadcrumb>
          <BreadcrumbList>
            {breadcrumbFolders.length > 0 ? (
              breadcrumbFolders.map((folder, index) => {
                const isLast = index === breadcrumbFolders.length - 1;

                return (
                  <Fragment key={folder.id}>
                    <BreadcrumbItem>
                      {isLast ? (
                        <BreadcrumbPage>{folder.name}</BreadcrumbPage>
                      ) : (
                        <BreadcrumbLink
                          className="cursor-pointer"
                          onClick={() => void onOpenFolder(folder.id)}
                        >
                          {folder.name}
                        </BreadcrumbLink>
                      )}
                    </BreadcrumbItem>
                    {!isLast ? <BreadcrumbSeparator /> : null}
                  </Fragment>
                );
              })
            ) : (
              <BreadcrumbItem>
                <BreadcrumbPage>Workspace</BreadcrumbPage>
              </BreadcrumbItem>
            )}
          </BreadcrumbList>
        </Breadcrumb>

        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-4xl tracking-[-0.05em] text-foreground sm:text-5xl">
              File management
            </h1>
          </div>

          <div className="flex items-center gap-2">
            {share ? (
              <Badge variant="outline">{share.permission_level}</Badge>
            ) : null}
            <Badge variant={share ? "default" : "secondary"}>
              {share ? "Active share" : "No share"}
            </Badge>
          </div>
        </div>
      </div>

      <FieldGroup className="grid gap-3 lg:grid-cols-[1fr_160px_150px_120px]">
        <Field>
          <FieldLabel htmlFor="workspace-search">Search</FieldLabel>
          <FieldContent>
            <div className="relative">
              <SearchIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                id="workspace-search"
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search by folder or file name"
                value={searchQuery}
              />
            </div>
          </FieldContent>
        </Field>

        <Field>
          <FieldLabel>Sort by</FieldLabel>
          <FieldContent>
            <Select
              onValueChange={(value) => setSortKey(value as SortKey)}
              value={sortKey}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Sort field" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="name">Name</SelectItem>
                  <SelectItem value="updated_at">Updated</SelectItem>
                  <SelectItem value="size">Size</SelectItem>
                  <SelectItem value="type">Type</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </FieldContent>
        </Field>

        <Field>
          <FieldLabel>Direction</FieldLabel>
          <FieldContent>
            <Select
              onValueChange={(value) =>
                setSortDirection(value as "asc" | "desc")
              }
              value={sortDirection}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Direction" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="asc">Ascending</SelectItem>
                  <SelectItem value="desc">Descending</SelectItem>
                </SelectGroup>
              </SelectContent>
            </Select>
          </FieldContent>
        </Field>

        <Field>
          <FieldLabel>Page size</FieldLabel>
          <FieldContent>
            <Select
              onValueChange={(value) => setPageSize(Number(value))}
              value={String(pageSize)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Size" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {PAGE_SIZE_OPTIONS.map((size) => (
                    <SelectItem key={size} value={size}>
                      {size}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </FieldContent>
        </Field>
      </FieldGroup>
    </div>
  );
}

export function WorkspacePagination({
  pageIndex,
  pageSize,
  pending,
  setPageIndex,
  totalItems,
  totalPages,
}: WorkspacePaginationProps) {
  const pages = buildPaginationItems(pageIndex, totalPages);

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
      <p className="text-sm text-muted-foreground">
        Showing {totalItems ? (pageIndex - 1) * pageSize + 1 : 0} to{" "}
        {Math.min(pageIndex * pageSize, totalItems)} of {totalItems} items
      </p>
      <Pagination className="mx-0 w-auto justify-start lg:justify-end">
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious
              disabled={pageIndex === 1 || pending}
              onClick={() =>
                setPageIndex((current) => Math.max(1, current - 1))
              }
            />
          </PaginationItem>
          {pages.map((page, index) => (
            <PaginationItem key={`${page}-${index}`}>
              {page === "ellipsis" ? (
                <PaginationEllipsis />
              ) : (
                <PaginationLink
                  disabled={pending}
                  isActive={page === pageIndex}
                  onClick={() => setPageIndex(page)}
                >
                  {page}
                </PaginationLink>
              )}
            </PaginationItem>
          ))}
          <PaginationItem>
            <PaginationNext
              disabled={pending || pageIndex >= totalPages}
              onClick={() =>
                setPageIndex((current) => Math.min(totalPages, current + 1))
              }
            />
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  );
}

function buildPaginationItems(
  pageIndex: number,
  totalPages: number,
): Array<number | "ellipsis"> {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  if (pageIndex <= 3) {
    return [1, 2, 3, 4, "ellipsis", totalPages];
  }

  if (pageIndex >= totalPages - 2) {
    return [
      1,
      "ellipsis",
      totalPages - 3,
      totalPages - 2,
      totalPages - 1,
      totalPages,
    ];
  }

  return [
    1,
    "ellipsis",
    pageIndex - 1,
    pageIndex,
    pageIndex + 1,
    "ellipsis",
    totalPages,
  ];
}
