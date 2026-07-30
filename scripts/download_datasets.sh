#!/usr/bin/env bash
# Download the three public source datasets into data/raw/ (git-ignored).
# These feed the profiling notebooks ONLY — the simulator itself reads the
# fitted params in simulation/params/, so these downloads are a one-time step.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw/{lendingclub,ipinyou,criteo}

echo "== 1/3 LendingClub (Kaggle: wordsforthewise/lending-club) =="
# Prereq: pip install kaggle; API token at ~/.kaggle/kaggle.json (kaggle.com -> Account -> Create New Token)
kaggle datasets download -d wordsforthewise/lending-club -p data/raw/lendingclub --unzip

echo "== 2/3 iPinYou RTB seasons 2-3 =="
cat <<'EOF'
Manual step: download from https://contest.ipinyou.com/ mirror at
  https://data.computational-advertising.org  (ipinyou.contest.dataset, seasons 2-3)
Place the season archives under data/raw/ipinyou/ . The full set is large (~35GB
uncompressed); for calibration a 3-5 day sample per season is sufficient.
EOF

echo "== 3/3 Criteo Uplift v2 =="
curl -L -o data/raw/criteo/criteo-uplift-v2.1.csv.gz \
  http://go.criteo.net/criteo-research-uplift-v2.1.csv.gz

echo "Done. Next: run the profiling notebooks in analysis/profiling/ (see docs/calibration_spec.md §5)."
