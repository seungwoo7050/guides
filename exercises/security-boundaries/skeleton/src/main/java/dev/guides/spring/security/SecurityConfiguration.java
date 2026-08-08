package dev.guides.spring.security;

import tools.jackson.databind.json.JsonMapper;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.AccessDeniedHandler;

@Configuration(proxyBeanMethods = false)
public class SecurityConfiguration {
  @Bean
  UserDetailsService users(PasswordEncoder encoder) {
    return new InMemoryUserDetailsManager(
        User.withUsername("owner")
            .password(encoder.encode("owner-password"))
            .roles("EDITOR")
            .build(),
        User.withUsername("viewer")
            .password(encoder.encode("viewer-password"))
            .roles("VIEWER")
            .build());
  }

  @Bean
  PasswordEncoder passwordEncoder() {
    return org.springframework.security.crypto.factory.PasswordEncoderFactories
        .createDelegatingPasswordEncoder();
  }

  @Bean
  SecurityFilterChain securityFilterChain(HttpSecurity http, JsonMapper mapper)
      throws Exception {
    return http
        .authorizeHttpRequests(authorize -> authorize.anyRequest().permitAll())
        .csrf(csrf -> csrf.disable())
        .httpBasic(Customizer.withDefaults())
        .exceptionHandling(errors -> errors
            .authenticationEntryPoint(authenticationEntryPoint(mapper))
            .accessDeniedHandler(accessDeniedHandler(mapper)))
        .build();
  }

  private AuthenticationEntryPoint authenticationEntryPoint(JsonMapper mapper) {
    return (request, response, exception) -> writeProblem(
        response,
        mapper,
        HttpStatus.UNAUTHORIZED,
        "AUTHENTICATION_REQUIRED",
        "인증이 필요합니다.");
  }

  private AccessDeniedHandler accessDeniedHandler(JsonMapper mapper) {
    return (request, response, exception) -> writeProblem(
        response,
        mapper,
        HttpStatus.FORBIDDEN,
        "ACCESS_DENIED",
        "요청을 수행할 권한이 없습니다.");
  }

  private void writeProblem(
      HttpServletResponse response,
      JsonMapper mapper,
      HttpStatus status,
      String errorCode,
      String detail) throws java.io.IOException {
    ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
    problem.setProperty("errorCode", errorCode);
    response.setStatus(status.value());
    response.setContentType(MediaType.APPLICATION_PROBLEM_JSON_VALUE);
    mapper.writeValue(response.getOutputStream(), problem);
  }
}
