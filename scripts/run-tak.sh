#!/usr/bin/env bash
set -e
TR=/opt/tak

# Ensure anything not having the correct config loads certs and saves logs to the volume
# (yes, we do need to re-check at every start)
if [[ ! -L "${TR}/certs"  ]];then
  mv ${TR}/certs ${TR}/certs.orig
  ln -s "${TR}/data/certs/" "${TR}/certs"
fi
if [[ ! -L "${TR}/logs"  ]];then
  mv ${TR}/logs ${TR}/logs.orig
  ln -s "${TR}/data/logs/" "${TR}/logs"
fi

# Change to workdir
cd ${TR}
export TAK_PROFILE="$1"
if [[ -z "${LOGGING_CONFIG:-}" ]]; then
    LOGGING_CONFIG=$(/usr/bin/python3 /opt/scripts/logging_config.py "$1")
fi
export LOGGING_CONFIG
export LOGGING_STRUCTURED_ECS_SERVICE_NAME="${LOGGING_STRUCTURED_ECS_SERVICE_NAME:-tak-server-$1}"
total_kib=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
: "${CONFIG_MAX_HEAP:=$((total_kib / 35000))}"
: "${MESSAGING_MAX_HEAP:=$((total_kib / 6300))}"
: "${API_MAX_HEAP:=$((total_kib / 6300))}"
: "${RETENTION_MAX_HEAP:=$((total_kib / 30000))}"
: "${PLUGIN_MANAGER_MAX_HEAP:=$((total_kib / 30000))}"

case "$1" in
  config|messaging|api)
    export LOADER_MAIN=org.opendefence.tak.ServerLauncher
    export JDK_JAVA_OPTIONS="${JDK_JAVA_OPTIONS} -Dloader.path=WEB-INF/lib-provided,WEB-INF/lib,WEB-INF/classes,file:lib/"
    ;;
esac
if [[ "${TAK_AUTH_MODE:-legacy}" == strict && ( "$1" == messaging || "$1" == api ) ]]; then
    export JDK_JAVA_OPTIONS="${JDK_JAVA_OPTIONS} -Dopendefence.tak.role=$1 -javaagent:/opt/tak/lib/strict-fingerprint-agent.jar"
    if [[ "$1" == api ]]; then
        export JDK_JAVA_OPTIONS="${JDK_JAVA_OPTIONS} -Dopendefence.tak.integrationAdminCertificate=/identities/integration-admin/tls.crt"
    fi
fi

# Start the right process
if [ $1 = "messaging" ]; then
    echo "Starting TAK Messaging"
    exec java -jar -Xmx${MESSAGING_MAX_HEAP}m -Dspring.profiles.active=messaging,consolelog -Dkeystore.pkcs12.legacy takserver.war
elif [ $1 = "config" ]; then
    echo "Starting TAK config"
    exec java -jar -Xmx${CONFIG_MAX_HEAP}m -Dspring.profiles.active=config,consolelog takserver.war
elif [ $1 = "api" ]; then
    echo "Starting TAK API"
    # TAK applies CoreConfig keystore overrides only to additional connectors.
    # Its primary HTTPS connector reads Spring's SSL properties instead.
    export SERVER_SSL_KEY_STORE="${TAK_HTTPS_KEYSTORE_FILENAME:-/opt/tak/data/certs/files/takserver-https.jks}"
    export SERVER_SSL_KEY_STORE_PASSWORD="${TAK_HTTPS_CERT_PASS:-${TAKSERVER_CERT_PASS}}"
    exec java -jar -Xmx${API_MAX_HEAP}m -Dspring.profiles.active=api,consolelog -Dkeystore.pkcs12.legacy takserver.war
elif [ $1 = "retention" ]; then
    echo "Starting TAK Retention"
    exec java -jar -Xmx${RETENTION_MAX_HEAP}m takserver-retention.jar
elif [ $1 = "pm" ]; then
    echo "Starting TAK Plugin Manager"
    exec java -jar -Xmx${PLUGIN_MANAGER_MAX_HEAP}m -Dloader.main=fi.pvarki.tak.PluginLauncher -Dloader.path=WEB-INF/lib-provided,WEB-INF/lib,WEB-INF/classes,file:lib/ takserver-pm.jar
else
  echo "Please provide right TAK component: messaging, config, api, retention or pm"
fi
