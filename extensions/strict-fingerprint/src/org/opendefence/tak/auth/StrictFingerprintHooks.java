package org.opendefence.tak.auth;

import java.lang.reflect.Method;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.time.Clock;

/** Entry points called by the pinned TAK bytecode before it forwards client traffic. */
public final class StrictFingerprintHooks {
    private static final StrictFingerprintPolicy POLICY = new StrictFingerprintPolicy(Clock.systemUTC());

    private StrictFingerprintHooks() {}

    static StrictFingerprintPolicy policy() {
        return POLICY;
    }

    public static void messaging(Object connection) {
        X509Certificate leaf = (X509Certificate) call(connection, "getCert");
        if (leaf == null) throw new SecurityException("Client certificate required");
        try {
            require(StrictFingerprintPolicy.commonName(leaf), leaf);
        } catch (CertificateException denied) {
            throw new SecurityException(denied.getMessage(), denied);
        }
    }

    public static void user(Object user) {
        require((String) call(user, "getName"), (X509Certificate) call(user, "getCert"));
    }

    public static boolean http(Object request, Object authentication) {
        try {
            Object value = call(request, "getAttribute", String.class,
                    "jakarta.servlet.request.X509Certificate");
            if (!(value instanceof X509Certificate[] chain) || chain.length == 0) return false;
            require((String) call(authentication, "getName"), chain[0]);
            return true;
        } catch (RuntimeException denied) {
            return false;
        }
    }

    private static void require(String accountId, X509Certificate leaf) {
        try {
            POLICY.requireApproved(accountId, leaf);
        } catch (CertificateException denied) {
            throw new SecurityException(denied.getMessage(), denied);
        }
    }

    private static Object call(Object target, String method) {
        if (target == null) throw new SecurityException("Client identity required");
        try {
            return target.getClass().getMethod(method).invoke(target);
        } catch (ReflectiveOperationException invalid) {
            throw new SecurityException("Authentication hook target changed", invalid);
        }
    }

    private static Object call(Object target, String method, Class<?> argumentType, Object argument) {
        if (target == null) throw new SecurityException("HTTP request required");
        try {
            Method getter = target.getClass().getMethod(method, argumentType);
            return getter.invoke(target, argument);
        } catch (ReflectiveOperationException invalid) {
            throw new SecurityException("HTTP authentication hook target changed", invalid);
        }
    }
}
