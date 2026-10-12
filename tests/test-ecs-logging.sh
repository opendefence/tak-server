#!/usr/bin/env bash
# Test external configuration with the selected image's own logging libraries.
set -euo pipefail
image=${1:?Usage: test-ecs-logging.sh IMAGE}
root=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$root/outputs"
work=$(mktemp -d "$root/outputs/ecs-probe.XXXXXX")
trap 'rm -rf "$work"' EXIT
docker run --rm --pull=never --network none \
  -e "HOST_UID=$(id -u)" -e "HOST_GID=$(id -g)" \
  -v "$work:/work" --entrypoint /bin/bash "$image" -ceu '
    trap '\''chown -R "$HOST_UID:$HOST_GID" /work'\'' EXIT
    cd /work
    unzip -q /opt/tak/takserver.war "WEB-INF/classes/*" "WEB-INF/lib/*"
    for role in config messaging api retention pm; do
      configuration=$(/usr/bin/python3 /opt/scripts/logging_config.py "$role")
      cp "$configuration" "/work/$role.xml"
    done
  '
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -v "$work:/work" -v "$root/tests:/tests:ro" \
  eclipse-temurin:17-jdk-noble@sha256:fb79620c3f6ee8f1c7530a8dc4fd49e3b410bcef037694ad4858a1553bac4170 \
  bash -ceu '
    classpath="/work:/work/WEB-INF/classes:/work/WEB-INF/lib/*"
    javac -cp "$classpath" -d /work /tests/LoggingProbe.java
    printf "<configuration/>" > /work/quiet.xml
    for json in false true; do
      for role in config messaging api retention pm; do
        mkdir -p "/work/run/$json/$role"
        cd "/work/run/$json/$role"
        java -Dlogback.configurationFile=/work/quiet.xml \
          -Dlogging.json.enabled="$json" -Dlogging.audit.enabled=true -cp "$classpath" \
          LoggingProbe "$role" "/work/$role.xml"
      done
    done
  '
