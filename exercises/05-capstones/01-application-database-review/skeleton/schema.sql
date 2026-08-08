-- TODO: 조직 경계와 상태 불변식을 제약으로 표현한다.
CREATE TABLE organizations (id bigint, name text);
CREATE TABLE users (id bigint, email text);
CREATE TABLE memberships (org_id bigint, user_id bigint, role text);
CREATE TABLE projects (id bigint, org_id bigint, name text);
CREATE TABLE tickets (
    id bigint,
    project_id bigint,
    org_id bigint,
    reporter_id bigint,
    assignee_id bigint,
    title text,
    status text,
    severity text,
    created_at timestamptz,
    closed_at timestamptz
);
