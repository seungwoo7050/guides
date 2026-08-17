import type { ColumnType, Generated } from "kysely";


export interface SchemaMigrationTable {
  version: string;
  applied_at: Generated<Date>;
}

export interface UserTable {
  id: Generated<string>;
  handle: string;
  display_name: string;
  role: "user" | "admin";
  status: "active" | "suspended";
  created_at: Generated<Date>;
}

export interface SessionTable {
  token: string;
  user_id: string;
  expires_at: Date;
  created_at: Generated<Date>;
}

export interface BoardTable {
  id: Generated<string>;
  owner_id: string;
  title: string;
  version: Generated<number>;
  closed_at: Date | null;
  created_at: Generated<Date>;
}

export interface BoardMemberTable {
  board_id: string;
  user_id: string;
  role: "owner" | "editor" | "viewer";
  joined_at: Generated<Date>;
}

export interface BoardItemTable {
  id: Generated<string>;
  board_id: string;
  kind: "note" | "shape";
  content: string;
  x: number;
  y: number;
  width: Generated<number>;
  height: Generated<number>;
  version: Generated<number>;
  updated_by: string;
  updated_at: Generated<Date>;
}

export interface BoardEventTable {
  id: Generated<string>;
  board_id: string;
  sequence: ColumnType<number, number, never>;
  actor_id: string;
  event_type: string;
  payload: unknown;
  created_at: Generated<Date>;
}

export interface AdminActionTable {
  id: Generated<string>;
  actor_id: string;
  target_user_id: string;
  action: "suspend" | "restore";
  reason: string;
  created_at: Generated<Date>;
}

export interface Database {
  schema_migrations: SchemaMigrationTable;
  users: UserTable;
  sessions: SessionTable;
  boards: BoardTable;
  board_members: BoardMemberTable;
  board_items: BoardItemTable;
  board_events: BoardEventTable;
  admin_actions: AdminActionTable;
}
