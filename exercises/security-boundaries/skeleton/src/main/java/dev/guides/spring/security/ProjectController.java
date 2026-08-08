package dev.guides.spring.security;

import jakarta.validation.Valid;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/projects")
public class ProjectController {
  private final ProjectStore projects;

  public ProjectController(ProjectStore projects) {
    this.projects = projects;
  }

  @GetMapping("/{projectId}")
  public ProjectResponse find(@PathVariable long projectId) {
    return projects.find(projectId);
  }

  @PostMapping("/{projectId}/rename")
  @PreAuthorize("@projectAccess.canEdit(#projectId, authentication.name)")
  public ProjectResponse rename(
      @PathVariable long projectId,
      @Valid @RequestBody RenameProjectRequest request) {
    return projects.rename(projectId, request.title());
  }
}
