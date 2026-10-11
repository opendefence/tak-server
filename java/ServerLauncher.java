package org.opendefence.tak;

import com.bbn.marti.remote.config.LocalConfiguration;
import java.nio.file.Path;
import tak.server.ServerConfiguration;

/** Select the actual role file before the unchanged server initializes. */
public final class ServerLauncher {
    private ServerLauncher() {}

    public static void main(String[] args) throws Exception {
        String configured = System.getenv("TAKCL_CORECONFIG_PATH");
        if (configured == null || configured.isBlank()) {
            throw new IllegalStateException("TAKCL_CORECONFIG_PATH is required");
        }
        Path path = Path.of(configured);
        if (!path.isAbsolute()) {
            throw new IllegalStateException("CoreConfig path must be absolute");
        }
        if (LocalConfiguration.CONFIG_FILE != null) {
            throw new IllegalStateException("CoreConfig initialized before path selection");
        }
        // JAXBUtils creates .backup beside this path, replacing destination symlinks.
        LocalConfiguration.CONFIG_FILE = path.toRealPath().toString();
        boolean strict = "strict".equals(System.getenv("TAK_AUTH_MODE"));
        if (strict
                && !"config".equals(System.getenv("TAK_PROFILE"))) {
            String role = System.getProperty("opendefence.tak.role");
            if ("messaging".equals(role)) {
                Class.forName("com.bbn.marti.nio.codec.impls.X509AuthCodec", false,
                        Thread.currentThread().getContextClassLoader());
                Class.forName("com.bbn.marti.groups.X509Authenticator", false,
                        Thread.currentThread().getContextClassLoader());
            } else if ("api".equals(role)) {
                Class.forName("org.springframework.security.web.access.intercept.FilterSecurityInterceptor",
                        false, Thread.currentThread().getContextClassLoader());
            } else {
                throw new IllegalStateException("Strict authentication role is missing");
            }
            Class<?> agent = Class.forName("org.opendefence.tak.auth.StrictFingerprintAgent");
            agent.getMethod("requireInstalled", String.class).invoke(null, role);
        }
        if (args.length == 1 && "--check-strict-hooks".equals(args[0])) {
            if (!strict || "config".equals(System.getenv("TAK_PROFILE"))) {
                throw new IllegalStateException("Strict authentication hooks are not active");
            }
            System.out.println("Strict authentication hooks installed for "
                    + System.getProperty("opendefence.tak.role"));
            return;
        }
        ServerConfiguration.main(args);
    }
}
