#!/bin/sh
set -eu

engine=${CONTAINER_ENGINE:-docker}
image=${1:?usage: test-strict-agent.sh image}

probe() {
    "$engine" run --rm --pull=never --network none --entrypoint sh \
        -e TAK_AUTH_MODE=strict -e TAKCL_CORECONFIG_PATH=/tmp/strict-hook-test.xml \
        "$image" -c '
            printf "<Configuration/>" >/tmp/strict-hook-test.xml
            cd /opt/tak
            exec java -Dloader.main=org.opendefence.tak.ServerLauncher \
                -Dloader.path=WEB-INF/lib-provided,WEB-INF/lib,WEB-INF/classes,file:lib/ \
                -Dopendefence.tak.role="$1" \
                -javaagent:/opt/tak/lib/strict-fingerprint-agent.jar \
                -jar takserver.war --check-strict-hooks
        ' sh "$1"
}

for role in messaging api; do
    output=$(probe "$role")
    [ "$output" = "Strict authentication hooks installed for $role" ]
done

if "$engine" run --rm --pull=never --network none --entrypoint sh \
    -e TAK_AUTH_MODE=strict -e TAKCL_CORECONFIG_PATH=/tmp/strict-hook-test.xml \
    "$image" -c '
        printf "<Configuration/>" >/tmp/strict-hook-test.xml
        cd /opt/tak
        exec java -Dloader.main=org.opendefence.tak.ServerLauncher \
            -Dloader.path=WEB-INF/lib-provided,WEB-INF/lib,WEB-INF/classes,file:lib/ \
            -Dopendefence.tak.role=messaging -jar takserver.war --check-strict-hooks
    ' >/dev/null 2>&1; then
    echo 'Strict startup succeeded without its agent' >&2
    exit 1
fi

if output=$("$engine" run --rm --pull=never --network none --entrypoint java \
    -v "$PWD/README.rst:/opt/tak/utils/UserManager.jar:ro" \
    "$image" -Dopendefence.tak.role=messaging \
    -javaagent:/opt/tak/lib/strict-fingerprint-agent.jar -version 2>&1); then
    echo 'Strict startup accepted a changed vendor JAR' >&2
    exit 1
else
    status=$?
    [ "$status" -eq 70 ]
    printf '%s\n' "$output" | grep -Fq 'Unsupported vendor artifact'
fi

echo 'Strict agent installation and fail-closed probes passed'
