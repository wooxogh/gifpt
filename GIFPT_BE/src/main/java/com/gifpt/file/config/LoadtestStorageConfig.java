package com.gifpt.file.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;

import com.gifpt.file.service.S3StorageService;

@Configuration
@Profile("loadtest")
public class LoadtestStorageConfig {

    @Bean
    @Primary
    public S3StorageService loadtestS3StorageService() {
        return new S3StorageService(null, "loadtest") {
            @Override
            public boolean objectExists(String key) {
                return false;
            }
        };
    }
}
