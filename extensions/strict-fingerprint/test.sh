#!/bin/sh
set -eu
cd /work
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=fixture-ca -keyout ca.key -out ca.pem 2>/dev/null
for name in main tak-only unapproved other duplicate-cn duplicate-cn-rdn multivalued-rdn missing-cn; do
  subject=/CN=00000000-0000-4000-8000-000000000001
  case "$name" in
    other) subject=/CN=00000000-0000-4000-8000-000000000002 ;;
    duplicate-cn) subject="$subject/CN=00000000-0000-4000-8000-000000000001" ;;
    duplicate-cn-rdn) subject="$subject+CN=00000000-0000-4000-8000-000000000001" ;;
    multivalued-rdn) subject="$subject+OU=fixture" ;;
    missing-cn) subject=/OU=fixture ;;
  esac
  openssl req -new -newkey rsa:2048 -nodes -subj "$subject" -keyout "$name.key" -out "$name.csr" 2>/dev/null
  openssl x509 -req -in "$name.csr" -CA ca.pem -CAkey ca.key -CAcreateserial -days 1 -out "$name.pem" 2>/dev/null
  openssl verify -CAfile ca.pem "$name.pem"
done
javac --release 17 -Xlint:all -Werror -d /work/classes \
  /extension/src/org/opendefence/tak/auth/StrictFingerprintPolicy.java \
  /extension/tests/StrictFingerprintPolicyTest.java
java -ea -cp /work/classes StrictFingerprintPolicyTest
