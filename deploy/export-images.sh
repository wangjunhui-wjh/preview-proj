#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd "$SCRIPT_DIR/.." && pwd)
MANIFEST="$SCRIPT_DIR/images.manifest"
OUTPUT="$SCRIPT_DIR/image-bundles/eia-ai-images-0.2.0.tar"
BUILD=0
DRY_RUN=0
SKIP_IMAGE_CHECK=0

usage() {
  cat <<'EOF'
Usage: ./deploy/export-images.sh [--build] [--output FILE] [--dry-run]

Exports the exact local images listed in deploy/images.manifest as one Docker
archive. The archive contains no .env, model key, task data, Caddy certificate
or Hermes session data. Run --build first on a connected release machine when
the three project images are not already present.
EOF
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --build) BUILD=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --output)
      [ "$#" -ge 2 ] || die '--output requires a file path.'
      OUTPUT=$2
      shift
      ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
  shift
done

command -v docker >/dev/null 2>&1 || die 'Docker was not found.'
docker info >/dev/null 2>&1 || die 'Docker daemon is not running or accessible.'
[ -f "$MANIFEST" ] || die "Missing image manifest: $MANIFEST"

if [ "$BUILD" -eq 1 ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '%s\n' "docker build -f $PROJECT_ROOT/Dockerfile.backend -t eia-ai-backend:0.2.0 $PROJECT_ROOT"
    printf '%s\n' "docker build -f $PROJECT_ROOT/Dockerfile.hermes -t eia-ai-hermes-controller:0.2.0 $PROJECT_ROOT"
    printf '%s\n' "docker build -f $PROJECT_ROOT/Dockerfile.hermes-tools -t eia-ai-hermes-tools:0.2.0 $PROJECT_ROOT"
    printf '%s\n' 'docker pull caddy:2-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648'
    printf '%s\n' 'docker pull alpine:3.21@sha256:48b0309ca019d89d40f670aa1bc06e426dc0931948452e8491e3d65087abc07d'
    SKIP_IMAGE_CHECK=1
  else
    docker build -f "$PROJECT_ROOT/Dockerfile.backend" -t eia-ai-backend:0.2.0 "$PROJECT_ROOT"
    docker build -f "$PROJECT_ROOT/Dockerfile.hermes" -t eia-ai-hermes-controller:0.2.0 "$PROJECT_ROOT"
    docker build -f "$PROJECT_ROOT/Dockerfile.hermes-tools" -t eia-ai-hermes-tools:0.2.0 "$PROJECT_ROOT"
    docker pull 'caddy:2-alpine@sha256:5f5c8640aae01df9654968d946d8f1a56c497f1dd5c5cda4cf95ab7c14d58648'
    docker pull 'alpine:3.21@sha256:48b0309ca019d89d40f670aa1bc06e426dc0931948452e8491e3d65087abc07d'
  fi
fi

images=''
missing=0
while IFS='|' read -r image _role _source; do
  case "$image" in ''|'#'*) continue ;; esac
  images="${images}${images:+ }$image"
  if [ "$SKIP_IMAGE_CHECK" -eq 0 ] && ! docker image inspect "$image" >/dev/null 2>&1; then
    printf 'Missing image: %s\n' "$image" >&2
    missing=1
  fi
done < "$MANIFEST"
[ "$missing" -eq 0 ] || die 'Build or pull the missing images, then retry with --build if appropriate.'

output_dir=$(dirname "$OUTPUT")
if [ "$DRY_RUN" -eq 1 ]; then
  printf '%s\n' "mkdir -p $output_dir"
  printf '%s\n' "docker save --output $OUTPUT $images"
  printf '%s\n' "copy $MANIFEST to ${OUTPUT}.manifest.txt and write ${OUTPUT}.sha256"
  exit 0
fi

mkdir -p "$output_dir"
docker save --output "$OUTPUT" $images
cp "$MANIFEST" "${OUTPUT}.manifest.txt"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$OUTPUT" > "${OUTPUT}.sha256"
elif command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$OUTPUT" > "${OUTPUT}.sha256"
else
  printf '%s\n' 'Warning: no SHA-256 command found; archive checksum was not created.' >&2
fi

printf 'Offline image archive created: %s\n' "$OUTPUT"
printf '%s\n' 'Transfer the archive, its .manifest.txt and .sha256 sidecar together.'
