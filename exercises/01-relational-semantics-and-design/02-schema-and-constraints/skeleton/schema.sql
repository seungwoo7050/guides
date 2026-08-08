-- TODO: 업무 불변식을 데이터베이스 제약으로 옮긴다.
CREATE TABLE users (
    id bigint,
    email text
);

CREATE TABLE projects (
    id bigint,
    owner_id bigint,
    name text
);

CREATE TABLE memberships (
    project_id bigint,
    user_id bigint,
    role text
);

CREATE TABLE tasks (
    id bigint,
    project_id bigint,
    assignee_id bigint,
    title text,
    priority integer,
    status text,
    completed_at timestamptz
);
