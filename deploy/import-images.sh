#!/bin/sh
set -eu

ARCHIVE=''
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: ./deploy/import-images.sh ARCHIVE.tar [--dry-run]

Verifies ARCHIVE.tar against an adjacent .sha256 file when present, then loads
the Docker images locally. It never imports configuration, model credentials or
runtime project data.
EOF
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    -*) die "Unknown option: $1" ;;
    *)
      [ -z "$ARCHIVE" ] || die 'Only one archive path is allowed.'
      ARCHIVE=$1
      ;;
  esac
  shift
done

[ -n "$ARCHIVE" ] || { usage >&2; exit 2; }
[ -f "$ARCHIVE" ] || die "Archive not found: $ARCHIVE"
command -v docker >/dev/null 2>&1 || die 'Docker was not found.'
docker info >/dev/null 2>&1 || die 'Docker daemon is not running or accessible.'

checksum="${ARCHIVE}.sha256"
if [ -f "$checksum" ]; then
  if command -v sha256sum >/dev/null 2>&1; then
    expected=$(awk 'NR == 1 { print $1 }' "$checksum")
    actual=$(sha256sum "$ARCHIVE" | awk '{print $1}')
    [ "$expected" = "$actual" ] || die 'SHA-256 verification failed.'
    printf '%s\n' 'SHA-256 verification passed.'
  elif command -v shasum >/dev/null 2>&1; then
    expected=$(awk '{print $1}' "$checksum")
    actual=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')
    [ "$expected" = "$actual" ] || die 'SHA-256 verification failed.'
    printf '%s\n' 'SHA-256 verification passed.'
  else
    printf '%s\n' 'Warning: no SHA-256 command found; archive checksum was not verified.' >&2
  fi
else
  printf '%s\n' 'Warning: adjacent .sha256 file not found; archive checksum was not verified.' >&2
fi

if [ "$DRY_RUN" -eq 1 ]; then
  printf '%s\n' "docker load --input $ARCHIVE"
  exit 0
fi

docker load --input "$ARCHIVE"
manifest="${ARCHIVE}.manifest.txt"
if [ -f "$manifest" ]; then
  printf 'Imported image manifest: %s\n' "$manifest"
fi
printf '%s\n' 'Images imported. Copy the source release, configure the selected deploy/*/.env, then run its start script.'
