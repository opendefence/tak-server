import ch.qos.logback.classic.LoggerContext;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.boot.logging.LoggingInitializationContext;
import org.springframework.boot.logging.logback.LogbackLoggingSystem;
import org.springframework.core.env.StandardEnvironment;

/** Exercise the exact bundled encoder, including escaping and retained files. */
public final class LoggingProbe {
    private static final ObjectMapper JSON = new ObjectMapper();

    private static void check(String lines, String role) throws Exception {
        if (lines.isBlank()) throw new AssertionError("No log records");
        for (String line : lines.lines().toList()) {
            JsonNode event = JSON.readTree(line);
            Instant.parse(event.path("@timestamp").asText());
            if (!event.at("/ecs/version").asText().equals("8.11")
                    || !event.at("/service/name").asText().equals("tak-server-" + role)
                    || event.at("/log/level").asText().isEmpty()
                    || event.at("/log/logger").asText().isEmpty()) {
                throw new AssertionError("Missing ECS fields: " + event);
            }
            if (event.path("message").asText().contains("probe")
                    || event.at("/log/logger").asText().equals("ecs-probe")) {
                if (!event.at("/trace/id").asText().equals("probe-trace")) {
                    throw new AssertionError("MDC lost: " + event);
                }
            }
            if (event.path("message").asText().startsWith("failure")) {
                if (!event.at("/error/type").asText().equals("java.lang.IllegalStateException")
                        || !event.at("/error/stack_trace").asText().contains("quoted \"error\"")) {
                    throw new AssertionError("Exception details lost: " + event);
                }
            }
        }
    }

    public static void main(String[] args) throws Exception {
        String role = args[0];
        System.setProperty("logging.structured.ecs.service.name", "tak-server-" + role);
        StandardEnvironment environment = new StandardEnvironment();
        environment.setActiveProfiles(role, "consolelog");
        PrintStream original = System.out;
        ByteArrayOutputStream captured = new ByteArrayOutputStream();
        System.setOut(new PrintStream(captured, true, StandardCharsets.UTF_8));
        LogbackLoggingSystem logging = new LogbackLoggingSystem(LoggingProbe.class.getClassLoader());
        logging.beforeInitialize();
        logging.initialize(new LoggingInitializationContext(environment), args[1], null);
        captured.reset();
        MDC.put("trace.id", "probe-trace");
        var logger = LoggerFactory.getLogger("ecs-probe");
        logger.info("quoted \"value\"\nUnicode: å {}", "argument");
        logger.error("failure\nsecond line", new IllegalStateException("quoted \"error\"\nnext line"));
        LoggerFactory.getLogger("http_access_logger").info("access probe");
        LoggerFactory.getLogger("IntrusionDetector").warn("security probe");
        ((LoggerContext) LoggerFactory.getILoggerFactory()).stop();
        System.setOut(original);
        String console = captured.toString(StandardCharsets.UTF_8);
        check(console, role);
        boolean messagePreserved = false;
        for (String line : console.lines().toList()) {
            messagePreserved |= JSON.readTree(line).path("message").asText()
                    .equals("quoted \"value\"\nUnicode: å argument");
        }
        if (!messagePreserved) {
            throw new AssertionError("Message escaping or formatting changed: " + console);
        }
        String application = role.equals("pm") ? "plugins" : role;
        check(Files.readString(Path.of("logs/takserver-" + application + ".log")), role);
        if (role.equals("api")) {
            check(Files.readString(Path.of("logs/takserver-api-access.log")), role);
            check(Files.readString(Path.of("logs/takserver-esapi.log")), role);
        }
        System.out.println("PASS: " + role + " ECS console, files, MDC, escaping and exceptions");
    }
}
