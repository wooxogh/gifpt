package com.gifpt.analysis.cache;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Profile;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Map;

@Component
@Profile("loadtest")
public class StatusCache {
    private static final Duration TTL = Duration.ofSeconds(2);
    private static final String KEY_PREFIX = "gifpt:status:";

    @Autowired private StringRedisTemplate redis;
    @Autowired private ObjectMapper mapper;

    public Map<String, Object> get(long jobId) {
        String json = redis.opsForValue().get(KEY_PREFIX + jobId);
        if (json == null) return null;
        try {
            return mapper.readValue(json, Map.class);
        } catch (Exception e) {
            return null;
        }
    }

    public void put(long jobId, Map<String, Object> value) {
        try {
            redis.opsForValue().set(KEY_PREFIX + jobId, mapper.writeValueAsString(value), TTL);
        } catch (Exception e) {
            // Fail open: cache write errors must not poison the request path.
        }
    }
}
