#!/usr/bin/env bash
# Test external configuration with the selected image's own logging libraries.
set -euo pipefail
image=${1:?Usage: test-logging.sh IMAGE}
root=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$root/outputs"
work=$(mktemp -d "$root/outputs/logging-probe.XXXXXX")
trap 'rm -rf "$work"' EXIT
docker run --rm --pull=never --network none \
  -e "HOST_UID=$(id -u)" -e "HOST_GID=$(id -g)" \
  -v "$work:/work" --entrypoint /bin/bash "$image" -ceu '
    trap '\''chown -R "$HOST_UID:$HOST_GID" /work'\'' EXIT
    cd /work
    [[ "$TAK_LOG_FORMAT" == utc ]]
    if TAK_LOG_FORMAT=invalid /usr/bin/python3 /opt/scripts/logging_config.py config 2>/work/invalid.log; then
      echo "Invalid logging format was accepted" >&2
      exit 1
    fi
    grep -q "TAK_LOG_FORMAT must be ecs, utc, or local" /work/invalid.log
    unzip -q /opt/tak/takserver.war "WEB-INF/classes/*" "WEB-INF/lib/*"
    for format in ecs utc local; do
      for role in config messaging api retention pm; do
        configuration=$(TAK_LOG_FORMAT=$format /usr/bin/python3 /opt/scripts/logging_config.py "$role")
        cp "$configuration" "/work/$format-$role.xml"
      done
    done
  '
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -v "$work:/work" -v "$root/tests:/tests:ro" \
  eclipse-temurin:17-jdk-noble@sha256:fb79620c3f6ee8f1c7530a8dc4fd49e3b410bcef037694ad4858a1553bac4170 \
  bash -ceu '
    classpath="/work:/work/WEB-INF/classes:/work/WEB-INF/lib/*"
    javac -cp "$classpath" -d /work /tests/LoggingProbe.java
    printf "<configuration/>" > /work/quiet.xml
    for format in ecs utc local; do
      for json in false true; do
        for role in config messaging api retention pm; do
          mkdir -p "/work/run/$format/$json/$role"
          cd "/work/run/$format/$json/$role"
          java -Duser.timezone=Pacific/Honolulu -Dlogback.configurationFile=/work/quiet.xml \
            -Dlogging.json.enabled="$json" -Dlogging.audit.enabled=true -cp "$classpath" \
            LoggingProbe "$role" "/work/$format-$role.xml" "$format"
        done
      done
    done
  '
