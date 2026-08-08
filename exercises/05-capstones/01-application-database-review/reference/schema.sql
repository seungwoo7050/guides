CREATE TABLE organizations (
    id bigint PRIMARY KEY,
    name text NOT NULL UNIQUE
);

CREATE TABLE users (
    id bigint PRIMARY KEY,
    email text NOT NULL
);
CREATE UNIQUE INDEX users_email_ci_uq ON users(lower(email));

CREATE TABLE memberships (
    org_id bigint NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('OWNER', 'MEMBER')),
    PRIMARY KEY (org_id, user_id)
);

CREATE TABLE projects (
    id bigint PRIMARY KEY,
    org_id bigint NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name text NOT NULL CHECK (btrim(name) <> ''),
    UNIQUE (id, org_id),
    UNIQUE (org_id, name)
);

CREATE TABLE tickets (
    id bigint PRIMARY KEY,
    project_id bigint NOT NULL,
    org_id bigint NOT NULL,
    reporter_id bigint NOT NULL,
    assignee_id bigint,
    title text NOT NULL CHECK (btrim(title) <> ''),
    status text NOT NULL CHECK (status IN ('OPEN', 'IN_PROGRESS', 'DONE')),
    severity text NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    created_at timestamptz NOT NULL,
    closed_at timestamptz,
    FOREIGN KEY (project_id, org_id) REFERENCES projects(id, org_id) ON DELETE CASCADE,
    FOREIGN KEY (org_id, reporter_id) REFERENCES memberships(org_id, user_id),
    FOREIGN KEY (org_id, assignee_id) REFERENCES memberships(org_id, user_id),
    CHECK (
        (status = 'DONE' AND closed_at IS NOT NULL)
        OR
        (status <> 'DONE' AND closed_at IS NULL)
    )
);
