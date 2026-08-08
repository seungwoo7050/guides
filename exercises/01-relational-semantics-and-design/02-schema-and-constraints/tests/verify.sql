INSERT INTO users(id, email) VALUES
    (1, 'owner@example.test'),
    (2, 'member@example.test'),
    (3, 'outsider@example.test');
INSERT INTO projects(id, owner_id, name) VALUES (10, 1, 'database-guide');
INSERT INTO memberships(project_id, user_id, role) VALUES
    (10, 1, 'OWNER'),
    (10, 2, 'EDITOR');
INSERT INTO tasks(id, project_id, assignee_id, title, priority, status, completed_at)
VALUES (100, 10, 2, 'valid task', 3, 'OPEN', NULL);

DO $$
BEGIN
    BEGIN
        INSERT INTO users(id, email) VALUES (4, 'OWNER@EXAMPLE.TEST');
        RAISE EXCEPTION 'case-insensitive duplicate email was accepted';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO memberships(project_id, user_id, role) VALUES (10, 2, 'VIEWER');
        RAISE EXCEPTION 'duplicate membership was accepted';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO memberships(project_id, user_id, role) VALUES (10, 3, 'ADMIN');
        RAISE EXCEPTION 'invalid role was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO tasks(id, project_id, assignee_id, title, priority, status)
        VALUES (101, 10, 3, 'outsider', 2, 'OPEN');
        RAISE EXCEPTION 'non-member assignee was accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO tasks(id, project_id, assignee_id, title, priority, status)
        VALUES (102, 10, 2, 'bad priority', 9, 'OPEN');
        RAISE EXCEPTION 'invalid priority was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO tasks(id, project_id, assignee_id, title, priority, status, completed_at)
        VALUES (103, 10, 2, 'missing completion time', 2, 'DONE', NULL);
        RAISE EXCEPTION 'DONE without completed_at was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO tasks(id, project_id, assignee_id, title, priority, status, completed_at)
        VALUES (104, 10, 2, 'early completion time', 2, 'OPEN', now());
        RAISE EXCEPTION 'OPEN with completed_at was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
END $$;

DO $$
BEGIN
    BEGIN
        INSERT INTO projects(id, owner_id, name) VALUES (11, 999, 'orphan project');
        RAISE EXCEPTION 'project with missing owner was accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO projects(id, owner_id, name) VALUES (12, 1, 'database-guide');
        RAISE EXCEPTION 'duplicate project name per owner was accepted';
    EXCEPTION WHEN unique_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO tasks(id, project_id, assignee_id, title, priority, status)
        VALUES (105, 10, 2, '   ', 2, 'OPEN');
        RAISE EXCEPTION 'blank task title was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO tasks(id, project_id, assignee_id, title, priority, status)
        VALUES (106, 10, 2, 'invalid state', 2, 'BLOCKED');
        RAISE EXCEPTION 'invalid task status was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
END $$;
