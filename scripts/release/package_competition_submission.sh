#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PROJECT_NAME="A22"
OUT_BASE_DIR="${ROOT_DIR}/dist/submission"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
SKIP_BUILD="false"
SKIP_IMAGES="false"
SKIP_ENGINEERING="false"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/release/package_competition_submission.sh [options]

Options:
  --project-name NAME   Package name prefix (default: A22)
  --out-dir DIR         Output base directory (default: ./dist/submission)
  --skip-build          Skip docker compose build and export existing local images
  --skip-images         Skip docker image tar export
  --skip-engineering    Skip engineering project archives
  -h, --help            Show this help

Examples:
  ./scripts/release/package_competition_submission.sh
  ./scripts/release/package_competition_submission.sh --project-name A22_Final --out-dir /root/autodl-tmp/a22/submission
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-name)
      PROJECT_NAME="$2"
      shift 2
      ;;
    --out-dir)
      OUT_BASE_DIR="$2"
      shift 2
      ;;
    --skip-build)
      SKIP_BUILD="true"
      shift
      ;;
    --skip-images)
      SKIP_IMAGES="true"
      shift
      ;;
    --skip-engineering)
      SKIP_ENGINEERING="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[error] unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[error] required command not found: $cmd" >&2
    exit 1
  fi
}

ensure_repo_layout() {
  local required=(
    "${ROOT_DIR}/compose.yaml"
    "${ROOT_DIR}/compose.remote.models.yaml"
    "${ROOT_DIR}/remote/avatar-service"
    "${ROOT_DIR}/remote/speech-service"
    "${ROOT_DIR}/scripts/remote/start_remote_stack_tmux.sh"
  )
  local path
  for path in "${required[@]}"; do
    if [[ ! -e "$path" ]]; then
      echo "[error] required path missing: $path" >&2
      exit 1
    fi
  done
}

write_sha256() {
  local file_path="$1"
  local out_file="$2"
  sha256sum "$file_path" | awk '{print $1}' >"$out_file"
}

PACKAGE_ROOT="${OUT_BASE_DIR}/${PROJECT_NAME}_competition_submission_${TIMESTAMP}"
IMAGES_DIR="${PACKAGE_ROOT}/01_docker_images"
ENGINEERING_DIR="${PACKAGE_ROOT}/02_engineering_projects"
META_DIR="${PACKAGE_ROOT}/99_manifest"
TMP_STAGE_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${TMP_STAGE_DIR}"
}
trap cleanup EXIT

require_cmd tar
require_cmd sha256sum
ensure_repo_layout

mkdir -p "${PACKAGE_ROOT}" "${META_DIR}"
if [[ "${SKIP_IMAGES}" != "true" ]]; then
  mkdir -p "${IMAGES_DIR}"
fi
if [[ "${SKIP_ENGINEERING}" != "true" ]]; then
  mkdir -p "${ENGINEERING_DIR}"
fi

cd "${ROOT_DIR}"

if [[ "${SKIP_IMAGES}" != "true" ]]; then
  require_cmd docker

  SERVICES=(
    "qwen-server"
    "speech-service"
    "vision-service"
    "avatar-service"
    "orchestrator"
  )
  IMAGES=(
    "a22/qwen-server:latest"
    "a22/speech-service:latest"
    "a22/vision-service:latest"
    "a22/avatar-service:latest"
    "a22/orchestrator:latest"
  )

  if [[ "${SKIP_BUILD}" != "true" ]]; then
    echo "[info] building remote model stack images..."
    docker compose -f compose.yaml -f compose.remote.models.yaml build "${SERVICES[@]}"
  else
    echo "[info] skip build enabled, exporting existing local images..."
  fi

  local_image
  for local_image in "${IMAGES[@]}"; do
    if ! docker image inspect "$local_image" >/dev/null 2>&1; then
      echo "[error] image not found locally: $local_image" >&2
      echo "[hint] run without --skip-build, or build the image first." >&2
      exit 1
    fi
  done

  IMAGE_TAR="${IMAGES_DIR}/${PROJECT_NAME}_remote_stack_images.tar"
  echo "[info] exporting images to ${IMAGE_TAR} ..."
  docker save "${IMAGES[@]}" -o "${IMAGE_TAR}"
  write_sha256 "${IMAGE_TAR}" "${IMAGE_TAR}.sha256"

  {
    echo "docker_images:"
    printf '  - %s\n' "${IMAGES[@]}"
  } > "${META_DIR}/docker_images_list.txt"
fi

if [[ "${SKIP_ENGINEERING}" != "true" ]]; then
  echo "[info] packaging engineering projects..."

  AVATAR_STAGE="${TMP_STAGE_DIR}/avatar_engineering"
  SPEECH_STAGE="${TMP_STAGE_DIR}/speech_engineering"
  mkdir -p "${AVATAR_STAGE}" "${SPEECH_STAGE}"

  mkdir -p "${AVATAR_STAGE}/remote" "${AVATAR_STAGE}/scripts" "${AVATAR_STAGE}/shared"
  cp -a "${ROOT_DIR}/remote/avatar-service" "${AVATAR_STAGE}/remote/avatar-service"
  cp -a "${ROOT_DIR}/scripts/remote/start_remote_stack_tmux.sh" "${AVATAR_STAGE}/scripts/"
  cp -a "${ROOT_DIR}/scripts/remote/stop_remote_stack_tmux.sh" "${AVATAR_STAGE}/scripts/"
  cp -a "${ROOT_DIR}/scripts/remote/restart_avatar_service_soulx_full.sh" "${AVATAR_STAGE}/scripts/"
  cp -a "${ROOT_DIR}/shared/contracts" "${AVATAR_STAGE}/shared/contracts"
  cp -a "${ROOT_DIR}/compose.remote.models.yaml" "${AVATAR_STAGE}/"
  cp -a "${ROOT_DIR}/.env.remote.models.example" "${AVATAR_STAGE}/"

  cat > "${AVATAR_STAGE}/README_SUBMISSION.txt" <<'EOF'
Package purpose:
- Executable digital human facial behavior driving model project files.

Main entry:
- remote/avatar-service

Recommended startup helper scripts:
- scripts/restart_avatar_service_soulx_full.sh
- scripts/start_remote_stack_tmux.sh

Model paths are externalized by environment variables (not bundled here).
EOF

  mkdir -p "${SPEECH_STAGE}/remote" "${SPEECH_STAGE}/scripts" "${SPEECH_STAGE}/shared"
  cp -a "${ROOT_DIR}/remote/speech-service" "${SPEECH_STAGE}/remote/speech-service"
  cp -a "${ROOT_DIR}/scripts/remote/start_remote_stack_tmux.sh" "${SPEECH_STAGE}/scripts/"
  cp -a "${ROOT_DIR}/scripts/remote/stop_remote_stack_tmux.sh" "${SPEECH_STAGE}/scripts/"
  cp -a "${ROOT_DIR}/shared/contracts" "${SPEECH_STAGE}/shared/contracts"
  cp -a "${ROOT_DIR}/compose.remote.models.yaml" "${SPEECH_STAGE}/"
  cp -a "${ROOT_DIR}/.env.remote.models.example" "${SPEECH_STAGE}/"

  cat > "${SPEECH_STAGE}/README_SUBMISSION.txt" <<'EOF'
Package purpose:
- Executable speech recognition model project files.

Main entry:
- remote/speech-service

Recommended startup helper scripts:
- scripts/start_remote_stack_tmux.sh

Model paths are externalized by environment variables (not bundled here).
EOF

  AVATAR_TAR="${ENGINEERING_DIR}/${PROJECT_NAME}_avatar_engineering.tar.gz"
  SPEECH_TAR="${ENGINEERING_DIR}/${PROJECT_NAME}_speech_asr_engineering.tar.gz"

  tar -czf "${AVATAR_TAR}" -C "${AVATAR_STAGE}" .
  tar -czf "${SPEECH_TAR}" -C "${SPEECH_STAGE}" .
  write_sha256 "${AVATAR_TAR}" "${AVATAR_TAR}.sha256"
  write_sha256 "${SPEECH_TAR}" "${SPEECH_TAR}.sha256"
fi

GIT_COMMIT="unknown"
GIT_BRANCH="unknown"
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_COMMIT="$(git rev-parse HEAD || true)"
  GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD || true)"
fi

cat > "${META_DIR}/submission_manifest.txt" <<EOF
project_name=${PROJECT_NAME}
generated_at=$(date -Iseconds)
host=$(hostname)
git_branch=${GIT_BRANCH}
git_commit=${GIT_COMMIT}
package_root=${PACKAGE_ROOT}
skip_build=${SKIP_BUILD}
skip_images=${SKIP_IMAGES}
skip_engineering=${SKIP_ENGINEERING}
EOF

cat > "${PACKAGE_ROOT}/README_SUBMISSION.txt" <<EOF
Competition submission package generated by:
  scripts/release/package_competition_submission.sh

Contents:
  01_docker_images/
    - ${PROJECT_NAME}_remote_stack_images.tar (if not skipped)
  02_engineering_projects/
    - ${PROJECT_NAME}_avatar_engineering.tar.gz (if not skipped)
    - ${PROJECT_NAME}_speech_asr_engineering.tar.gz (if not skipped)
  99_manifest/
    - submission_manifest.txt
    - docker_images_list.txt (if images exported)

Validation:
  sha256sum -c 01_docker_images/*.sha256 2>/dev/null || true
  sha256sum -c 02_engineering_projects/*.sha256 2>/dev/null || true
EOF

echo "[ok] competition submission package is ready:"
echo "  ${PACKAGE_ROOT}"

