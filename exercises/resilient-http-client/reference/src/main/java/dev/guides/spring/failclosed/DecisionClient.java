
package dev.guides.spring.failclosed;

import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class DecisionClient {
  private final RestClient client;
  private final int maxAttempts;

  public DecisionClient(RestClient decisionRestClient, DecisionClientProperties properties) {
    this.client = decisionRestClient;
    this.maxAttempts = properties.maxAttempts();
  }

  // [Implementation 3] 같은 request로 bounded retry하고 업무 거절과 장애를 분리한다.
  @CircuitBreaker(name = "decisionClient")
  public DecisionResponse check(DecisionRequest request) {
    DependencyUnavailableException lastFailure = null;
    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        DecisionResponse response =
            client
                .post()
                .uri("/decision")
                .body(request)
                .retrieve()
                .onStatus(
                    status -> status.value() == 409,
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
      } catch (DependencyUnavailableException exception) {
        lastFailure = exception;
      } catch (RestClientException exception) {
        lastFailure = new DependencyUnavailableException("외부 시스템을 사용할 수 없습니다.", exception);
      }
    }
    throw lastFailure;
  }
}
