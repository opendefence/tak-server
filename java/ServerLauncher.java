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
        ServerConfiguration.main(args);
    }
}
