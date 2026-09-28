#!/bin/sh
set -eu
umask 077

target=/opt/anna/deploy/anna-server/.env
if [ -e "$target" ]; then
  echo "Die Anna-Konfiguration existiert bereits. Abbruch ohne Überschreiben."
  exit 3
fi

printf "Easybell SIP-Benutzername: "
IFS= read -r easybell_user
printf "Easybell Contact User / Stammrufnummer (internationales Format): "
IFS= read -r contact_user
printf "Easybell SIP-Passwort (Eingabe bleibt unsichtbar): "
stty -echo
IFS= read -r easybell_password
stty echo
printf "\nOpenAI API-Key (Eingabe bleibt unsichtbar): "
stty -echo
IFS= read -r openai_key
stty echo
printf "\nAnna CRM-Webhook-Secret (Eingabe bleibt unsichtbar): "
stty -echo
IFS= read -r webhook_secret
stty echo
printf "\n"

for value in "$easybell_user" "$contact_user" "$easybell_password" "$openai_key" "$webhook_secret"; do
  if [ -z "$value" ]; then
    echo "Mindestens ein Pflichtwert fehlt. Es wurde nichts gespeichert."
    exit 2
  fi
done

internal_password=$(openssl rand -hex 32)
{
  printf "ANNA_INTERNAL_SIP_USERNAME=anna-aor\n"
  printf "ANNA_INTERNAL_SIP_PASSWORD=%s\n" "$internal_password"
  printf "PUBLIC_IP=46.225.221.42\n"
  printf "EASYBELL_SIP_USERNAME=%s\n" "$easybell_user"
  printf "EASYBELL_SIP_PASSWORD=%s\n" "$easybell_password"
  printf "EASYBELL_CONTACT_USER=%s\n" "$contact_user"
  printf "OPENAI_API_KEY=%s\n" "$openai_key"
  printf "ANNA_VOICE_WEBHOOK_SECRET=%s\n" "$webhook_secret"
} > "$target"
chmod 0600 "$target"
echo "Anna-Konfiguration wurde geschützt gespeichert."
echo "Es wurden keine Geheimnisse ausgegeben."
