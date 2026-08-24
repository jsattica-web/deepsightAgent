package com.deepsight.agent.service;

import com.deepsight.agent.dto.AgentChatRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

@Service
public class AgentService {

    private final RestTemplate restTemplate;
    private final String agentApiBaseUrl;

    public AgentService(
            @Value("${agent.api.base-url}") String agentApiBaseUrl,
            @Value("${agent.api.connect-timeout-ms:3000}") int connectTimeoutMs,
            @Value("${agent.api.read-timeout-ms:30000}") int readTimeoutMs) {
        this.agentApiBaseUrl = trimTrailingSlash(agentApiBaseUrl);
        this.restTemplate = createRestTemplate(connectTimeoutMs, readTimeoutMs);
    }

    public ResponseEntity<String> chat(AgentChatRequest request) {
        if (request == null || request.getQuestion() == null || request.getQuestion().trim().length() == 0) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .contentType(MediaType.APPLICATION_JSON_UTF8)
                    .body(createErrorResponse("INVALID_REQUEST", "question은 필수입니다."));
        }

        String url = agentApiBaseUrl + "/agent/chat";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        HttpEntity<AgentChatRequest> entity = new HttpEntity<AgentChatRequest>(request, headers);

        try {
            ResponseEntity<String> response = restTemplate.postForEntity(url, entity, String.class);
            return ResponseEntity.status(response.getStatusCode())
                    .contentType(MediaType.APPLICATION_JSON_UTF8)
                    .body(response.getBody());
        } catch (HttpStatusCodeException e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .contentType(MediaType.APPLICATION_JSON_UTF8)
                    .body(createErrorResponse("AGENT_SERVER_ERROR", e.getResponseBodyAsString()));
        } catch (ResourceAccessException e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .contentType(MediaType.APPLICATION_JSON_UTF8)
                    .body(createErrorResponse("AGENT_SERVER_ERROR", e.getMessage()));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .contentType(MediaType.APPLICATION_JSON_UTF8)
                    .body(createErrorResponse("INTERNAL_ERROR", e.getMessage()));
        }
    }

    private RestTemplate createRestTemplate(int connectTimeoutMs, int readTimeoutMs) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeoutMs);
        factory.setReadTimeout(readTimeoutMs);
        return new RestTemplate(factory);
    }

    private String trimTrailingSlash(String value) {
        if (value == null || value.trim().length() == 0) {
            return "http://localhost:8000";
        }

        String trimmed = value.trim();
        while (trimmed.endsWith("/")) {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        return trimmed;
    }

    private String createErrorResponse(String code, String detailMessage) {
        return "{"
                + "\"status\":\"error\","
                + "\"message\":\"Python Agent 서버 호출에 실패했습니다.\","
                + "\"data\":null,"
                + "\"error\":{"
                + "\"code\":\"" + escapeJson(code) + "\","
                + "\"message\":\"" + escapeJson(detailMessage) + "\""
                + "}"
                + "}";
    }

    private String escapeJson(String value) {
        if (value == null) {
            return "";
        }

        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < value.length(); i++) {
            char ch = value.charAt(i);
            if (ch == '\\') {
                builder.append("\\\\");
            } else if (ch == '"') {
                builder.append("\\\"");
            } else if (ch == '\n') {
                builder.append("\\n");
            } else if (ch == '\r') {
                builder.append("\\r");
            } else if (ch == '\t') {
                builder.append("\\t");
            } else {
                builder.append(ch);
            }
        }
        return builder.toString();
    }
}

