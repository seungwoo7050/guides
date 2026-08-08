package dev.guides.spring.testinfra;

import org.testcontainers.images.ImagePullPolicy;
import org.testcontainers.utility.DockerImageName;

public final class NeverPullPolicy implements ImagePullPolicy {
  @Override
  public boolean shouldPull(DockerImageName imageName) {
    return false;
  }
}
