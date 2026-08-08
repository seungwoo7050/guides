package dev.guides.spring.capstone;

import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.springframework.http.HttpStatusCode;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class PolicyClient {
  private final RestClient client;

  public PolicyClient(RestClient policyRestClient) {
    this.client = policyRestClient;
  }

  @CircuitBreaker(name = "policy")
  public void ensureAllowed(
      String actorId,
      CreatePublicationRequest request) {
    try {
      PolicyDecision decision = client.post()
          .uri("/policy/check")
          .body(new PolicyRequest(
              actorId,
              request.title(),
              request.source().toString()))
          .retrieve()
          .onStatus(
              status -> status.value() == 409,
              (httpRequest, response) -> {
                throw new PolicyRejectedException();
              })
          .body(PolicyDecision.class);
      if (decision == null || !decision.allowed()) {
        throw new PolicyRejectedException();
      }
    } catch (PolicyRejectedException exception) {
      throw exception;
    } catch (HttpClientErrorException exception) {
      HttpStatusCode status = exception.getStatusCode();
      throw new DependencyUnavailableException(
          "policy service가 예상하지 못한 응답을 반환했습니다: "
              + status.value(),
          exception);
    } catch (RestClientException exception) {
      throw new DependencyUnavailableException(
          "policy service를 사용할 수 없습니다.",
          exception);
    }
  }

  private record PolicyRequest(String actorId, String title, String source) {}

  private record PolicyDecision(boolean allowed) {}
}
