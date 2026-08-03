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

echo "== 2/3 iPinYou RTB seasons 2-3 (Kaggle mirror, sampled days per decision D4/Q5) =="
# Source: kaggle.com/datasets/lastsummer/ipinyou — the canonical ipinyou.contest.dataset
# tree (~6.3 GB compressed). The academic mirror (data.computational-advertising.org)
# was unreachable as of 2026-08-03. Calibration needs only a day sample per season:
# season 2 gets a weekend + two weekdays; season 3 gets its weekend + three weekdays
# (its per-day files are much smaller). All four record types per day: bid (bids +
# floor prices), imp (paying_price = winning price), clk, conv (CTR/CVR base rates).
IPINYOU_DS="lastsummer/ipinyou"
S2_DAYS="20130608 20130610 20130612"    # training2nd (season 2, June 2013)
S3_DAYS="20131019 20131020 20131021 20131022 20131023"  # training3rd (season 3, Oct 2013)

# Dataset-level metadata: README, checksums, city/region lookup tables
for f in README files.md5 city.en.txt region.en.txt; do
  kaggle datasets download -d "$IPINYOU_DS" -f "ipinyou.contest.dataset/${f}" \
    -p data/raw/ipinyou
done
# Per-day files, retried up to 3x (Kaggle sometimes drops connections)
for season in "training2nd:${S2_DAYS}" "training3rd:${S3_DAYS}"; do
  dir="${season%%:*}"; days="${season#*:}"
  mkdir -p "data/raw/ipinyou/${dir}"
  for day in $days; do
    for kind in bid imp clk conv; do
      f="ipinyou.contest.dataset/${dir}/${kind}.${day}.txt.bz2"
      for attempt in 1 2 3; do
        kaggle datasets download -d "$IPINYOU_DS" -f "$f" \
          -p "data/raw/ipinyou/${dir}" && break
        echo "retry ${attempt} failed for ${f}; sleeping"; sleep 15
      done
    done
  done
done
# Kaggle wraps single-file downloads in .zip; unpack any that arrived zipped
find data/raw/ipinyou -name '*.zip' -execdir unzip -o -q {} \; -delete

echo "== 3/3 Criteo Uplift v2 =="
curl -L -o data/raw/criteo/criteo-uplift-v2.1.csv.gz \
  http://go.criteo.net/criteo-research-uplift-v2.1.csv.gz

echo "Done. Next: run the profiling notebooks in analysis/profiling/ (see docs/calibration_spec.md §5)."
