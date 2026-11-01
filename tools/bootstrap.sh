#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .tools/vendor
checkout() {
  local name="$1" url="$2" rev="$3"
  if [[ ! -d ".tools/vendor/$name/.git" ]]; then
    git init -q ".tools/vendor/$name"
    git -C ".tools/vendor/$name" remote add origin "$url"
  fi
  if [[ -n "$(git -C ".tools/vendor/$name" status --porcelain)" ]]; then
    echo "Refusing to replace modified dependency: $name" >&2
    exit 1
  fi
  git -C ".tools/vendor/$name" fetch -q --depth 1 origin "$rev"
  git -C ".tools/vendor/$name" checkout -q --detach "$rev"
}
checkout hal https://github.com/STMicroelectronics/stm32h7xx-hal-driver.git fec141ce999da655a48e1a15db83a72d564a1312
checkout device https://github.com/STMicroelectronics/cmsis-device-h7.git e4d57d6edc39f35aced298732829fc2a5e6a8a71
checkout cmsis https://github.com/ARM-software/CMSIS_5.git 2b7495b8535bdcb306dac29b9ded4cfb679d7e5c
checkout tinyusb https://github.com/hathach/tinyusb.git 86ad6e56c1700e85f1c5678607a762cfe3aa2f47
