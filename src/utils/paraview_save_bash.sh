#!/usr/bin/env bash
set -euo pipefail

# Resolve repository root relative to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

RESULTS_ROOT="${REPO_ROOT}/data/results"
SAVE_ROOT="${REPO_ROOT}/data/paraview_saves"
PV_SCRIPT="${REPO_ROOT}/src/utils/paraview_save.py"

if ! command -v pvpython >/dev/null 2>&1; then
    echo "ERROR: pvpython is not on PATH. Activate the ParaView environment first." >&2
    exit 1
fi

if [[ ! -f "${PV_SCRIPT}" ]]; then
    echo "ERROR: ParaView script not found: ${PV_SCRIPT}" >&2
    exit 1
fi

if [[ ! -d "${RESULTS_ROOT}" ]]; then
    echo "ERROR: Results directory does not exist: ${RESULTS_ROOT}" >&2
    exit 1
fi

# Build a canonical, repository-local job list from existing .pvd files.
# Each job is stored as: "pvd_path|save_path"
declare -a jobs=()
while IFS= read -r -d '' pvd_path; do
    rel_path="${pvd_path#${RESULTS_ROOT}/}"
    save_path="${SAVE_ROOT}/${rel_path%/solution/u.pvd}/"
    mkdir -p "${save_path}"
    jobs+=("${pvd_path}|${save_path}")
done < <(find "${RESULTS_ROOT}" -type f -name 'u.pvd' -print0 | sort -z)

if [[ ${#jobs[@]} -eq 0 ]]; then
    echo "ERROR: No .pvd files found under ${RESULTS_ROOT}. Nothing to export." >&2
    exit 1
fi

export PARAVIEW_JOB_COUNT="${#jobs[@]}"
export PARAVIEW_JOBS
PARAVIEW_JOBS=$(printf '%s\n' "${jobs[@]}")

printf 'Found %s ParaView jobs in %s\n' "${PARAVIEW_JOB_COUNT}" "${RESULTS_ROOT}"
for job in "${jobs[@]}"; do
    pvd_path="${job%%|*}"
    save_path="${job#*|}"
    printf 'Running: %s -> %s\n' "${pvd_path}" "${save_path}"
    pvpython "${PV_SCRIPT}" \
        --pvd_path "${pvd_path}" \
        --save_path "${save_path}"
    printf '\n'
done

printf 'Completed %s ParaView jobs.\n' "${PARAVIEW_JOB_COUNT}"
