
package dev.guides.spring.failclosed;

import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class DecisionClient {
  private final RestClient client;

  public DecisionClient(RestClient decisionRestClient) {
    this.client = decisionRestClient;
  }

  @CircuitBreaker(name = "decisionClient")
  public DecisionResponse check(DecisionRequest request) {
    try {
      DecisionResponse response = client.post()
          .uri("/decision")
          .body(request)
          .retrieve()
          .onStatus(status -> status.value() == 409,
              (httpRequest, httpResponse) -> {
                throw new BusinessDeclineException("정책에 따라 요청을 처리할 수 없습니다.");
              })
          .body(DecisionResponse.class);
      if (response == null) {
        throw new DependencyUnavailableException("외부 시스템이 빈 응답을 반환했습니다.", null);
      }
      return response;
    } catch (BusinessDeclineException exception) {
      throw exception;
    } catch (RestClientException exception) {
      throw new DependencyUnavailableException("외부 시스템을 사용할 수 없습니다.", exception);
    }
  }
}
