package com.gifpt.security.auth.crypto;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;
import java.util.Base64;

@Converter
public class EncryptedStringAttributeConverter implements AttributeConverter<String, String> {
  private static final Logger log = LoggerFactory.getLogger(EncryptedStringAttributeConverter.class);

  private static final String TRANSFORMATION = "AES/GCM/NoPadding";
  private static final int GCM_TAG_LENGTH_BITS = 128;
  private static final int IV_LENGTH_BYTES = 12;
  private static final String PREFIX = "enc:v1:";
  private static final String ENV_KEY_NAME = "GIFPT_FIELD_ENCRYPTION_KEY";

  private static volatile SecretKeySpec cachedKey;
  private static volatile boolean missingKeyLogged;

  @Override
  public String convertToDatabaseColumn(String attribute) {
    if (attribute == null || attribute.isBlank()) {
      return attribute;
    }

    SecretKeySpec key = getKey();
    if (key == null) {
      // Keep service running for local/dev, but warn loudly.
      return attribute;
    }

    try {
      byte[] iv = new byte[IV_LENGTH_BYTES];
      new SecureRandom().nextBytes(iv);

      Cipher cipher = Cipher.getInstance(TRANSFORMATION);
      cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv));
      byte[] encrypted = cipher.doFinal(attribute.getBytes(java.nio.charset.StandardCharsets.UTF_8));

      byte[] payload = new byte[iv.length + encrypted.length];
      System.arraycopy(iv, 0, payload, 0, iv.length);
      System.arraycopy(encrypted, 0, payload, iv.length, encrypted.length);

      return PREFIX + Base64.getEncoder().encodeToString(payload);
    } catch (Exception e) {
      throw new IllegalStateException("Failed to encrypt sensitive field", e);
    }
  }

  @Override
  public String convertToEntityAttribute(String dbData) {
    if (dbData == null || dbData.isBlank()) {
      return dbData;
    }

    // Backward compatibility for existing plaintext rows.
    if (!dbData.startsWith(PREFIX)) {
      return dbData;
    }

    SecretKeySpec key = getKey();
    if (key == null) {
      throw new IllegalStateException("Encrypted field found, but encryption key is not configured");
    }

    try {
      byte[] payload = Base64.getDecoder().decode(dbData.substring(PREFIX.length()));
      if (payload.length <= IV_LENGTH_BYTES) {
        throw new IllegalStateException("Encrypted payload is malformed");
      }

      byte[] iv = new byte[IV_LENGTH_BYTES];
      byte[] encrypted = new byte[payload.length - IV_LENGTH_BYTES];
      System.arraycopy(payload, 0, iv, 0, IV_LENGTH_BYTES);
      System.arraycopy(payload, IV_LENGTH_BYTES, encrypted, 0, encrypted.length);

      Cipher cipher = Cipher.getInstance(TRANSFORMATION);
      cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv));
      byte[] plain = cipher.doFinal(encrypted);
      return new String(plain, java.nio.charset.StandardCharsets.UTF_8);
    } catch (Exception e) {
      throw new IllegalStateException("Failed to decrypt sensitive field", e);
    }
  }

  private SecretKeySpec getKey() {
    SecretKeySpec key = cachedKey;
    if (key != null) {
      return key;
    }

    String raw = System.getenv(ENV_KEY_NAME);
    if (raw == null || raw.isBlank()) {
      logMissingKeyOnce();
      return null;
    }

    try {
      byte[] decoded = Base64.getDecoder().decode(raw);
      if (decoded.length != 16 && decoded.length != 24 && decoded.length != 32) {
        throw new IllegalArgumentException("Key must be 16, 24, or 32 bytes after base64 decode");
      }
      cachedKey = new SecretKeySpec(decoded, "AES");
      return cachedKey;
    } catch (Exception e) {
      throw new IllegalStateException(
        ENV_KEY_NAME + " is invalid. Provide a base64-encoded AES key (16/24/32 bytes).", e
      );
    }
  }

  private void logMissingKeyOnce() {
    if (!missingKeyLogged) {
      missingKeyLogged = true;
      log.warn("{} is not set. Sensitive fields will be stored in plaintext.", ENV_KEY_NAME);
    }
  }
}
