export type ProjectStatus = "active" | "paused";

export type Project = {
  id: string;
  title: string;
  summary: string;
  status: ProjectStatus;
  version: number;
};

export type ProjectQuery = {
  q: string;
  status: "any" | ProjectStatus;
  page: number;
};

export type SearchResult = {
  projects: Project[];
  total: number;
  page: number;
  pageSize: number;
};

export type RenameProjectCommand = {
  id: string;
  title: string;
  version: number;
};

export type RenameOutcome =
  | { kind: "success"; project: Project }
  | { kind: "conflict"; project: Project; message: string }
  | { kind: "error"; message: string };
