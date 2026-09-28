#!/bin/sh
set -eu

required="ANNA_INTERNAL_SIP_USERNAME ANNA_INTERNAL_SIP_PASSWORD EASYBELL_SIP_USERNAME EASYBELL_SIP_PASSWORD EASYBELL_CONTACT_USER"
for name in $required; do
  eval "value=\${$name:-}"
  if [ -z "$value" ]; then
    echo "Missing required telephony configuration: $name" >&2
    exit 2
  fi
done

envsubst < /etc/asterisk/pjsip.conf.template > /etc/asterisk/pjsip.conf
chmod 0600 /etc/asterisk/pjsip.conf
exec /usr/sbin/asterisk -f
