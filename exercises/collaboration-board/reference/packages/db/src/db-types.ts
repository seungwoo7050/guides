import type { Generated } from "kysely";

// [Implementation 3-2]
// migration이 소유한 실제 열 이름과 nullable/generated 상태를 Kysely boundary에 그대로 옮깁니다.
// 이 mapping이 어긋나면 repository가 존재하지 않는 열을 type-safe하게 보이는 이름으로 사용할 수 있습니다.
export interface UserTable {
  id: Generated<string>;
  handle: string;
  display_name: string;
  role: Generated<"user" | "admin">;
  status: Generated<"active" | "suspended">;
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
  width: number;
  height: number;
  version: Generated<number>;
  updated_by: string;
  updated_at: Generated<Date>;
}
export interface BoardEventTable {
  id: Generated<string>;
  board_id: string;
  sequence: number;
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
export interface SchemaMigrationTable {
  version: string;
  applied_at: Generated<Date>;
}
export interface Database {
  users: UserTable;
  sessions: SessionTable;
  boards: BoardTable;
  board_members: BoardMemberTable;
  board_items: BoardItemTable;
  board_events: BoardEventTable;
  admin_actions: AdminActionTable;
  schema_migrations: SchemaMigrationTable;
}
