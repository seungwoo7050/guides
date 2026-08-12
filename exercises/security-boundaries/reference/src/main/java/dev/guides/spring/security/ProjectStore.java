package dev.guides.spring.security;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

// [Implementation 1] project state와 owner 판정의 정본을 한 component가 소유한다.
@Component
public final class ProjectStore {
  private final Map<Long, ProjectResponse> projects = new ConcurrentHashMap<>();

  public ProjectStore() {
    reset();
  }

  public ProjectResponse find(long id) {
    ProjectResponse project = projects.get(id);
    if (project == null) {
      throw new ProjectNotFoundException(id);
    }
    return project;
  }

  public boolean isOwner(long id, String username) {
    ProjectResponse project = projects.get(id);
    return project != null && project.owner().equals(username);
  }

  public ProjectResponse rename(long id, String title) {
    ProjectResponse current = find(id);
    ProjectResponse renamed = new ProjectResponse(id, current.owner(), title);
    projects.put(id, renamed);
    return renamed;
  }

  public void reset() {
    projects.clear();
    projects.put(1L, new ProjectResponse(1L, "owner", "초기 제목"));
  }
}
