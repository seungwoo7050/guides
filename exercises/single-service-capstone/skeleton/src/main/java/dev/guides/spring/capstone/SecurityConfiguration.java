package dev.guides.spring.capstone;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

@Configuration(proxyBeanMethods = false)
public class SecurityConfiguration {
  @Bean
  PasswordEncoder passwordEncoder() {
    return org.springframework.security.crypto.factory.PasswordEncoderFactories
        .createDelegatingPasswordEncoder();
  }

  @Bean
  UserDetailsService users(PasswordEncoder encoder) {
    return new InMemoryUserDetailsManager(
        User.withUsername("editor")
            .password(encoder.encode("editor-password"))
            .roles("EDITOR")
            .build(),
        User.withUsername("reader")
            .password(encoder.encode("reader-password"))
            .roles("READER")
            .build());
  }

  @Bean
  SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
    return http
        .csrf(csrf -> csrf.disable())
        .authorizeHttpRequests(authorize -> authorize.anyRequest().permitAll())
        .httpBasic(Customizer.withDefaults())
        .build();
  }
}
