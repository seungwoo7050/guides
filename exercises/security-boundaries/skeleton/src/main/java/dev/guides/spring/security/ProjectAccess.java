package dev.guides.spring.security;

import org.springframework.stereotype.Component;

@Component("projectAccess")
public final class ProjectAccess {
  private final ProjectStore projects;

  public ProjectAccess(ProjectStore projects) {
    this.projects = projects;
  }

  public boolean canEdit(long projectId, String username) {
    return projects.isOwner(projectId, username);
  }
}
