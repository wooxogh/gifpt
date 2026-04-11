package com.gifpt.file.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.HeadObjectRequest;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;

@Service
public class S3StorageService {

    private final S3Client s3Client;
    private final String bucket;

    public S3StorageService(
        S3Client s3Client,
        @Value("${gifpt.s3.bucket}") String bucket
    ) {
        this.s3Client = s3Client;
        this.bucket = bucket;
    }

    /**
     * Check whether an object exists in S3 using a HEAD request (~50ms, no download).
     *
     * @param key S3 object key, e.g. "animations/abc123.mp4"
     * @return true if the object exists, false if it does not
     */
    public boolean objectExists(String key) {
        try {
            s3Client.headObject(HeadObjectRequest.builder()
                    .bucket(bucket)
                    .key(key)
                    .build());
            return true;
        } catch (NoSuchKeyException e) {
            return false;
        }
    }
}
