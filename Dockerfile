########################################################################
# We can't do COPY --from=pvarki/tak-server-dist:$TAK_RELEASE  #
# So work around like this                                             #
########################################################################
ARG TEMURIN_VERSION="17"
ARG JAVA_RUNTIME_IMAGE="eclipse-temurin:${TEMURIN_VERSION}-jre-noble"
ARG JAVA_BUILD_IMAGE="eclipse-temurin:${TEMURIN_VERSION}-jdk-noble"
ARG TAK_RELEASE="5.8-RELEASE-92"
FROM pvarki/tak-server-dist:$TAK_RELEASE AS tak-files
RUN mv /zips/takserver-docker-*.zip /tmp/takserver.zip

FROM ${JAVA_RUNTIME_IMAGE} AS deps
ENV \
  LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
      openssl \
      python3-lxml \
      unzip \
      tini \
      curl \
      postgresql-client \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=hairyhenderson/gomplate:stable /gomplate /bin/gomplate
SHELL ["/bin/bash", "-lc"]


FROM deps AS unpack
COPY --from=tak-files /tmp/takserver.zip /tmp/takserver.zip
RUN cd /tmp \
    && unzip takserver.zip \
    && rm takserver.zip \
    && export DISTDIR=`echo takserver-docker-*` \
    && mv $DISTDIR"/tak" /opt/tak \
    && true

# Compile the external launcher against the selected vendor binary.
FROM ${JAVA_BUILD_IMAGE} AS plugin-launcher
COPY --from=unpack /opt/tak/takserver-pm.jar /tmp/takserver-pm.jar
COPY --from=unpack /opt/tak/takserver.war /tmp/takserver.war
COPY --from=unpack /opt/tak/db-utils/SchemaManager.jar /tmp/SchemaManager.jar
COPY java /tmp/tak-launcher
COPY extensions/strict-fingerprint/src /tmp/strict-fingerprint-src
WORKDIR /tmp/tak-plugin-api
RUN jar --extract --file /tmp/takserver-pm.jar BOOT-INF/classes BOOT-INF/lib \
    && javac --release 17 -cp '/tmp/tak-plugin-api/BOOT-INF/classes:/tmp/tak-plugin-api/BOOT-INF/lib/*' \
      -d /tmp/tak-launcher/classes /tmp/tak-launcher/PluginLauncher.java \
    && jar --extract --file /tmp/takserver.war WEB-INF/classes WEB-INF/lib WEB-INF/lib-provided \
    && javac --release 17 -cp '/tmp/tak-plugin-api/WEB-INF/classes:/tmp/tak-plugin-api/WEB-INF/lib/*:/tmp/tak-plugin-api/WEB-INF/lib-provided/*' \
      -d /tmp/tak-launcher/classes /tmp/tak-launcher/ServerLauncher.java \
    && javac --release 17 -cp /tmp/SchemaManager.jar \
      -d /tmp/tak-launcher/classes /tmp/tak-launcher/SchemaUpgrade.java \
    && jar --create --file /tmp/pvarki-launcher.jar -C /tmp/tak-launcher/classes . \
    && cp WEB-INF/lib/javassist-3.28.0-GA.jar /tmp/javassist.jar \
    && mkdir -p /tmp/strict-fingerprint-classes \
    && javac --release 17 -cp /tmp/javassist.jar -d /tmp/strict-fingerprint-classes \
      /tmp/strict-fingerprint-src/org/opendefence/tak/auth/*.java \
    && printf 'Premain-Class: org.opendefence.tak.auth.StrictFingerprintAgent\nClass-Path: javassist.jar\n' \
      > /tmp/strict-fingerprint-manifest \
    && jar --create --file /tmp/strict-fingerprint-agent.jar \
      --manifest /tmp/strict-fingerprint-manifest -C /tmp/strict-fingerprint-classes .

# Keep the distribution archive and build tools out of runtime layers.
FROM deps AS install
# CNPG requires TLS 1.3; retain TLS 1.2 for existing TAK peers.
ENV IGNITE_HOME=/opt/tak \
    JDK_JAVA_OPTIONS="-Dio.netty.tmpdir=/opt/tak -Djava.io.tmpdir=/opt/tak -Dio.netty.native.workdir=/opt/tak -Djava.net.preferIPv4Stack=true -Djava.security.egd=file:/dev/./urandom -DIGNITE_UPDATE_NOTIFIER=false -DIGNITE_QUIET=true -Djdk.tls.client.protocols=TLSv1.3,TLSv1.2 \
--add-opens=java.base/sun.security.pkcs=ALL-UNNAMED \
--add-opens=java.base/sun.security.pkcs10=ALL-UNNAMED \
--add-opens=java.base/sun.security.util=ALL-UNNAMED \
--add-opens=java.base/sun.security.x509=ALL-UNNAMED \
--add-opens=java.base/sun.security.tools.keytool=ALL-UNNAMED \
--add-opens=java.base/jdk.internal.misc=ALL-UNNAMED \
--add-opens=java.base/sun.nio.ch=ALL-UNNAMED \
--add-opens=java.management/com.sun.jmx.mbeanserver=ALL-UNNAMED \
--add-opens=jdk.internal.jvmstat/sun.jvmstat.monitor=ALL-UNNAMED \
--add-opens=java.base/sun.reflect.generics.reflectiveObjects=ALL-UNNAMED \
--add-opens=jdk.management/com.sun.management.internal=ALL-UNNAMED \
--add-opens=java.base/java.io=ALL-UNNAMED \
--add-opens=java.base/java.nio=ALL-UNNAMED \
--add-opens=java.base/java.util=ALL-UNNAMED \
--add-opens=java.base/java.util.concurrent=ALL-UNNAMED \
--add-opens=java.base/java.util.concurrent.locks=ALL-UNNAMED \
--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED \
--add-opens=java.base/java.lang=ALL-UNNAMED \
--add-opens=java.base/java.lang.invoke=ALL-UNNAMED \
--add-opens=java.base/java.math=ALL-UNNAMED \
--add-opens=java.sql/java.sql=ALL-UNNAMED \
--add-opens=java.base/javax.net.ssl=ALL-UNNAMED \
--add-opens=java.base/java.net=ALL-UNNAMED \
--add-opens=jdk.unsupported/sun.misc=ALL-UNNAMED \
--add-opens=java.base/java.lang.ref=ALL-UNNAMED \
--add-opens=java.base/java.lang.reflect=ALL-UNNAMED \
--add-opens=java.base/java.security=ALL-UNNAMED \
--add-opens=java.base/java.security.ssl=ALL-UNNAMED \
--add-opens=java.base/java.security.cert=ALL-UNNAMED \
--add-opens=java.base/sun.security.provider.certpath=ALL-UNNAMED \
--add-opens=java.base/sun.security.rsa=ALL-UNNAMED \
--add-opens=java.base/sun.security.ssl=ALL-UNNAMED \
--add-opens=java.base/sun.security.validator=ALL-UNNAMED \
--add-opens=java.base/sun.security.x500=ALL-UNNAMED \
--add-opens=jdk.crypto.cryptoki/sun.security.pkcs11=ALL-UNNAMED \
--add-opens=java.base/sun.security.pkcs12=ALL-UNNAMED \
--add-opens=java.base/sun.security.provider=ALL-UNNAMED \
--add-opens=java.base/javax.security.auth.x500=ALL-UNNAMED \
--add-opens=java.base/java.time=ALL-UNNAMED"
COPY --from=unpack /opt/tak /opt/tak
COPY --from=plugin-launcher /tmp/pvarki-launcher.jar /opt/tak/lib/pvarki-launcher.jar
COPY --from=plugin-launcher /tmp/strict-fingerprint-agent.jar /opt/tak/lib/strict-fingerprint-agent.jar
COPY --from=plugin-launcher /tmp/javassist.jar /opt/tak/lib/javassist.jar
COPY docker/entrypoint.sh /entrypoint.sh
COPY scripts /opt/scripts
COPY templates /opt/templates
COPY update /opt/tak/webcontent/update

FROM install AS run
ENV TAK_LOG_FORMAT=utc
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
