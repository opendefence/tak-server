#!/bin/sh
set -eu

war=${1:?usage: check-vendor-hooks.sh takserver.war UserManager.jar}
user_manager=${2:?usage: check-vendor-hooks.sh takserver.war UserManager.jar}
war=$(realpath "$war")
expected_war=64309513e45ba1e92084d457cd787b35d1c570ab918a11fd1ce1e5bdd4d6f26c
expected_user_manager=4ad7adcb9a09156d7122bfb2d4ddf3fd6705fb612f4d521335a5e08b449d24f6

check_hash() {
    actual=$(sha256sum "$2" | cut -d ' ' -f 1)
    if [ "$actual" != "$1" ]; then
        echo "Unsupported vendor artifact: $2 ($actual)" >&2
        exit 1
    fi
}

check_hash "$expected_war" "$war"
check_hash "$expected_user_manager" "$user_manager"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
cd "$work"
jar --extract --file "$war" \
    WEB-INF/classes/com/bbn/marti/nio/codec/impls/X509AuthCodec.class \
    WEB-INF/classes/com/bbn/marti/groups/X509Authenticator.class \
    WEB-INF/classes/com/bbn/marti/util/spring/TakAuthenticationProvider.class \
    WEB-INF/lib/spring-security-web-6.5.11.jar \
    WEB-INF/classes/security-context.xml

check_method() {
    if ! javap -p -s -classpath WEB-INF/classes "$1" | grep -Fq "$2"; then
        echo "Unsupported authentication hook: $1 $2" >&2
        exit 1
    fi
}

check_method com.bbn.marti.nio.codec.impls.X509AuthCodec 'protected synchronized void doTlsAuth();'
check_method com.bbn.marti.nio.codec.impls.X509AuthCodec 'public java.nio.ByteBuffer decode(java.nio.ByteBuffer);'
check_method com.bbn.marti.nio.codec.impls.X509AuthCodec 'public java.nio.ByteBuffer encode(java.nio.ByteBuffer);'
check_method com.bbn.marti.groups.X509Authenticator 'private com.bbn.marti.remote.groups.User auth(com.bbn.marti.remote.groups.User, com.bbn.marti.config.Input);'
check_method com.bbn.marti.util.spring.TakAuthenticationProvider 'public org.springframework.security.core.Authentication authenticate(org.springframework.security.core.Authentication)'
if ! javap -p -s -classpath WEB-INF/lib/spring-security-web-6.5.11.jar org.springframework.security.web.access.intercept.FilterSecurityInterceptor |
    grep -Fq 'public void doFilter(jakarta.servlet.ServletRequest, jakarta.servlet.ServletResponse, jakarta.servlet.FilterChain)'; then
    echo 'Unsupported HTTP authorization boundary' >&2
    exit 1
fi
grep -Fq 'X509AuthenticationFilter,' WEB-INF/classes/security-context.xml
grep -Fq 'FilterSecurityInterceptor" />' WEB-INF/classes/security-context.xml
grep -Fq 'class="com.bbn.marti.util.spring.TakAuthenticationProvider"' WEB-INF/classes/security-context.xml
echo 'Pinned TAK 5.8.84 authentication seams match'
