package dev.guides.spring.security;

import org.springframework.stereotype.Component;

@Component("projectAccess")
public final class ProjectAccess {
  private final ProjectStore projects;

  public ProjectAccess(ProjectStore projects) {
    this.projects = projects;
  }

  // [Implementation 2] 인증 이름을 object owner와 비교하는 권한 결정을 분리한다.
  public boolean canEdit(long projectId, String username) {
    return projects.isOwner(projectId, username);
  }
}
