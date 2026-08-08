package dev.guides.spring.security;

public final class ProjectNotFoundException extends RuntimeException {
  public ProjectNotFoundException(long id) {
    super("project를 찾을 수 없습니다: " + id);
  }
}
