package org.opendefence.tak.auth;

import java.io.ByteArrayInputStream;
import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.Instrumentation;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.ProtectionDomain;
import java.util.HexFormat;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import javassist.ClassClassPath;
import javassist.ClassPool;
import javassist.LoaderClassPath;

/** Pins transformed class bytes and halts on any incomplete strict installation. */
public final class StrictFingerprintAgent {
    private static final String WAR = "9f03a3c21e5ed09350fd92a2c16fed0dca246122dfb8f266e4179f3ca4134523"; // pragma: allowlist secret
    private static final String USER_MANAGER = "0fe547c2f4ce05d06a2e9724e0c2837eab0a0ba5be398390bb974b2385ce6f14"; // pragma: allowlist secret
    private static final String CODEC = "com/bbn/marti/nio/codec/impls/X509AuthCodec";
    private static final String AUTHENTICATOR = "com/bbn/marti/groups/X509Authenticator";
    private static final String HTTP = "org/springframework/security/web/access/intercept/FilterSecurityInterceptor";
    private static final String CODEC_HASH = "931567f9cfe8c65594d42531f7abc77361850bfd31632ac9e41658f6bcafa7dc"; // pragma: allowlist secret
    private static final String AUTHENTICATOR_HASH = "36cd42af013288a87e001e2694b2241d78fd2c7cd8687561bf0976978e36b275"; // pragma: allowlist secret
    private static final String HTTP_HASH = "c916dc2df009dc140b456965e602defdac3e0819259eb08b00cf8aaaabb0c633"; // pragma: allowlist secret
    private static final Set<String> INSTALLED = ConcurrentHashMap.newKeySet();
    private static volatile boolean active;

    private StrictFingerprintAgent() {}

    public static void premain(String ignored, Instrumentation instrumentation) {
        try {
            String role = System.getProperty("opendefence.tak.role");
            if (!"messaging".equals(role) && !"api".equals(role)) {
                throw new IllegalStateException("Strict agent requires messaging or api role");
            }
            check(Path.of("/opt/tak/takserver.war"), WAR);
            check(Path.of("/opt/tak/utils/UserManager.jar"), USER_MANAGER);
            instrumentation.addTransformer(new Hooks(role));
            active = true;
        } catch (Throwable failure) {
            fatal(failure);
        }
    }

    public static void requireInstalled(String role) {
        if (!active || !("messaging".equals(role) ? INSTALLED.containsAll(Set.of(CODEC, AUTHENTICATOR))
                : "api".equals(role) && INSTALLED.contains(HTTP))) {
            throw new IllegalStateException("Strict authentication hooks are incomplete for " + role);
        }
    }

    private static void check(Path file, String expected) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (var input = Files.newInputStream(file)) {
            byte[] block = new byte[65536];
            for (int count; (count = input.read(block)) != -1;) digest.update(block, 0, count);
        }
        if (!expected.equals(HexFormat.of().formatHex(digest.digest()))) {
            throw new SecurityException("Unsupported vendor artifact: " + file);
        }
    }

    private static void fatal(Throwable failure) {
        System.err.println("Strict authentication hook installation failed: " + failure);
        Runtime.getRuntime().halt(70);
    }

    private static final class Hooks implements ClassFileTransformer {
        private final String role;

        private Hooks(String role) {
            this.role = role;
        }

        @Override
        public byte[] transform(ClassLoader loader, String name, Class<?> redefining,
                ProtectionDomain domain, byte[] original) {
            if (!("messaging".equals(role) ? CODEC.equals(name) || AUTHENTICATOR.equals(name)
                    : HTTP.equals(name))) return null;
            try {
                String expected = CODEC.equals(name) ? CODEC_HASH
                        : AUTHENTICATOR.equals(name) ? AUTHENTICATOR_HASH : HTTP_HASH;
                String actual = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(original));
                if (!expected.equals(actual)) throw new SecurityException("Unsupported hook class: " + name);
                var pool = new ClassPool(true);
                pool.insertClassPath(new ClassClassPath(StrictFingerprintHooks.class));
                pool.insertClassPath(new LoaderClassPath(loader));
                var type = pool.makeClass(new ByteArrayInputStream(original));
                try {
                    if (CODEC.equals(name)) {
                        type.getDeclaredMethod("decode").insertBefore(
                                "org.opendefence.tak.auth.StrictFingerprintHooks.messaging(this.connectionInfo);");
                        type.getDeclaredMethod("encode").insertBefore(
                                "org.opendefence.tak.auth.StrictFingerprintHooks.messaging(this.connectionInfo);");
                    } else if (AUTHENTICATOR.equals(name)) {
                        type.getDeclaredMethod("auth").insertBefore(
                                "org.opendefence.tak.auth.StrictFingerprintHooks.user($1);");
                    } else {
                        type.getDeclaredMethod("doFilter").insertBefore(
                                "if (!org.opendefence.tak.auth.StrictFingerprintHooks.http($1, "
                                + "org.springframework.security.core.context.SecurityContextHolder"
                                + ".getContext().getAuthentication())) {"
                                + "((jakarta.servlet.http.HttpServletResponse)$2).sendError(403); return; }");
                    }
                    byte[] changed = type.toBytecode();
                    INSTALLED.add(name);
                    return changed;
                } finally {
                    type.detach();
                }
            } catch (Throwable failure) {
                fatal(failure);
                return null;
            }
        }
    }
}
