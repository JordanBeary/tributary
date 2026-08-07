"""Consumer population engine — the production implementation of design.md Section 3.2 stage 1.

Credit and demographic features consume ``simulation/params/lendingclub_marginals.json``
(produced and QA-gated by ``analysis/profiling/01_lendingclub.ipynb``) and nothing
else: the Gaussian copula over (loan_amnt, dti, annual_inc_log, fico_mid, emp_years)
is sampled exactly as the notebook's gated QA sampler does — multivariate normal
through the artifact's PSD-repaired sigma, normal-CDF to uniforms, inverse-CDF
through the artifact's 1000-point quantile tables, ordinal rank-map for employment
length (the n/a bucket excluded and renormalized, per the notebook's construction).
One deliberate divergence: ``fico_band`` is derived from the sampled ``fico_mid``
rather than drawn independently, so each row is internally coherent; the derived
band mix still lands within the ±1pp categorical gate (verified in tests).

Identity attributes (name, email, phone, address) sample Faker's en_US
frequency-weighted vocabularies through the stage RNG stream — vectorized numpy
draws over Faker's own name/street/city/domain data rather than per-row Faker
calls, keeping full-scale generation fast and every byte reproducible from one
seed. Zip codes are drawn from Faker's per-state ranges so they agree with the
LendingClub-calibrated ``addr_state``.

Duplicate records (design Section 2.3, ~8% of rows) share a person's hidden
``consumer_key`` with corrupted identity fields per the C7 mix: nickname 40% /
email typo 30% / new phone 20% / all three 10%. Credit features copy verbatim —
it is the same person applying again.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import json
import numpy as np
import pandas as pd
from scipy import stats

# Ordinal employment buckets from the fitting notebook (01_lendingclub Section 2).
# The n/a bucket is real applicant behavior in the source mix, but the copula
# excludes it, so generated consumers always carry observed tenure.
EMP_ORDER = ["< 1 year", "1 year", "2 years", "3 years", "4 years", "5 years",
             "6 years", "7 years", "8 years", "9 years", "10+ years"]
EMP_YEARS = {"< 1 year": 0.5, "1 year": 1, "2 years": 2, "3 years": 3,
             "4 years": 4, "5 years": 5, "6 years": 6, "7 years": 7,
             "8 years": 8, "9 years": 9, "10+ years": 10}

# FICO band edges matching the artifact's 5 bands (calibration spec Section 1)
FICO_EDGES = np.array([600, 660, 720, 780])
FICO_BANDS = np.array(["<600", "600-659", "660-719", "720-779", "780+"])

# C7 duplicate corruption mix (calibration spec Section 4)
CORRUPTIONS = np.array(["nickname", "email_typo", "new_phone", "all"])
CORRUPTION_PROBS = np.array([0.40, 0.30, 0.20, 0.10])

# Common US diminutives for the nickname corruption. Names without an entry fall
# back to a seeded single-character typo, so every "nickname" duplicate is
# guaranteed a first-name variant.
NICKNAMES = {
    "James": "Jim", "John": "Jack", "Robert": "Bob", "Michael": "Mike",
    "William": "Bill", "David": "Dave", "Richard": "Rick", "Joseph": "Joe",
    "Thomas": "Tom", "Charles": "Chuck", "Christopher": "Chris", "Daniel": "Dan",
    "Matthew": "Matt", "Anthony": "Tony", "Donald": "Don", "Steven": "Steve",
    "Andrew": "Andy", "Kenneth": "Ken", "Joshua": "Josh", "Edward": "Ed",
    "Ronald": "Ron", "Timothy": "Tim", "Jeffrey": "Jeff", "Gregory": "Greg",
    "Jacob": "Jake", "Nicholas": "Nick", "Jonathan": "Jon", "Stephen": "Steve",
    "Lawrence": "Larry", "Benjamin": "Ben", "Samuel": "Sam", "Alexander": "Alex",
    "Patrick": "Pat", "Zachary": "Zach", "Nathan": "Nate", "Peter": "Pete",
    "Raymond": "Ray", "Vincent": "Vince", "Theodore": "Ted", "Frederick": "Fred",
    "Eugene": "Gene", "Russell": "Russ", "Louis": "Lou", "Philip": "Phil",
    "Bradley": "Brad", "Douglas": "Doug", "Leonard": "Len", "Albert": "Al",
    "Elizabeth": "Liz", "Jennifer": "Jen", "Margaret": "Peggy", "Patricia": "Pat",
    "Katherine": "Kate", "Kathleen": "Kathy", "Deborah": "Deb", "Rebecca": "Becky",
    "Stephanie": "Steph", "Victoria": "Vicky", "Jessica": "Jess",
    "Samantha": "Sam", "Alexandra": "Alex", "Amanda": "Mandy", "Pamela": "Pam",
    "Cynthia": "Cindy", "Susan": "Sue", "Barbara": "Barb", "Sandra": "Sandy",
    "Judith": "Judy", "Kimberly": "Kim", "Angela": "Angie", "Abigail": "Abby",
    "Gabrielle": "Gabby", "Isabella": "Bella", "Danielle": "Dani",
    "Nicole": "Nikki", "Valerie": "Val", "Veronica": "Ronnie",
    "Jacqueline": "Jackie", "Catherine": "Cathy", "Dorothy": "Dottie",
    "Christina": "Tina", "Michelle": "Shelly", "Melissa": "Mel",
}


@dataclass(frozen=True)
class CreditModel:
    """The calibrated credit-feature parameterization, loaded verbatim from the artifact."""

    variables: list[str]        # copula variable order
    sigma: np.ndarray           # PSD-repaired Gaussian copula correlation
    probs: np.ndarray           # shared inverse-CDF probability grid
    quantiles: dict[str, np.ndarray]  # 1000-point tables per numeric marginal
    emp_edges: np.ndarray       # cumulative bucket edges, n/a excluded
    cat_labels: dict[str, np.ndarray]   # purpose, addr_state
    cat_probs: dict[str, np.ndarray]

    @classmethod
    def from_params_dir(cls, params_dir: Path | str) -> "CreditModel":
        p = json.loads((Path(params_dir) / "lendingclub_marginals.json").read_text())
        quantiles = {k: np.asarray(v["quantiles"], dtype=float)
                     for k, v in p["marginals"].items()}
        # emp_length rank-map: drop the n/a bucket and renormalize (notebook construction)
        emp = p["categoricals"]["emp_length"]
        emp_p = np.array([emp[k] for k in EMP_ORDER])
        cat_labels, cat_probs = {}, {}
        for cat in ("purpose", "addr_state"):
            freqs = p["categoricals"][cat]
            pv = np.array(list(freqs.values()))
            # JSON float round-trips can leave the vector at 1 - 1e-16
            cat_labels[cat] = np.array(list(freqs), dtype=object)
            cat_probs[cat] = pv / pv.sum()
        n_q = len(next(iter(quantiles.values())))
        return cls(
            variables=list(p["copula"]["variables"]),
            sigma=np.asarray(p["copula"]["gaussian_sigma"], dtype=float),
            probs=np.linspace(0.0, 1.0, n_q),
            quantiles=quantiles,
            emp_edges=np.cumsum(emp_p / emp_p.sum()),
            cat_labels=cat_labels,
            cat_probs=cat_probs,
        )


@dataclass(frozen=True)
class IdentityVocab:
    """Faker's en_US vocabularies, extracted once for vectorized seeded sampling."""

    first_names: np.ndarray
    first_probs: np.ndarray
    last_names: np.ndarray
    last_probs: np.ndarray
    street_suffixes: np.ndarray
    city_prefixes: np.ndarray
    city_suffixes: np.ndarray
    email_domains: np.ndarray
    zip_lo: dict[str, int]
    zip_hi: dict[str, int]

    @classmethod
    def from_faker(cls) -> "IdentityVocab":
        from faker.providers.address.en_US import Provider as Address
        from faker.providers.internet.en_US import Provider as Internet
        from faker.providers.person.en_US import Provider as Person

        def weighted(od):
            names = np.array(list(od), dtype=object)
            w = np.array(list(od.values()), dtype=float)
            return names, w / w.sum()

        first_names, first_probs = weighted(Person.first_names)
        last_names, last_probs = weighted(Person.last_names)
        return cls(
            first_names=first_names, first_probs=first_probs,
            last_names=last_names, last_probs=last_probs,
            street_suffixes=np.array(Address.street_suffixes, dtype=object),
            city_prefixes=np.array(Address.city_prefixes, dtype=object),
            city_suffixes=np.array(Address.city_suffixes, dtype=object),
            email_domains=np.array(Internet.free_email_domains, dtype=object),
            zip_lo={s: r[0] for s, r in Address.states_postcode.items()},
            zip_hi={s: r[1] for s, r in Address.states_postcode.items()},
        )


def sample_credit(model: CreditModel, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Sample n credit/demographic profiles — the notebook's gated QA sampler,
    plus fico_band derived from fico_mid for row-internal coherence."""
    z = rng.multivariate_normal(np.zeros(len(model.variables)), model.sigma,
                                size=n, method="cholesky")
    u = stats.norm.cdf(z)
    out: dict[str, np.ndarray] = {}
    for j, name in enumerate(model.variables):
        if name in model.quantiles:
            out[name] = np.interp(u[:, j], model.probs, model.quantiles[name])
        else:  # emp_years: ordinal rank-map through the bucket mix
            idx = np.searchsorted(model.emp_edges, u[:, j],
                                  side="right").clip(0, len(EMP_ORDER) - 1)
            out["emp_length"] = np.array(EMP_ORDER, dtype=object)[idx]
            out["emp_years"] = np.array([EMP_YEARS[l] for l in EMP_ORDER])[idx]
    for cat in ("purpose", "addr_state"):
        out[cat] = rng.choice(model.cat_labels[cat], size=n, p=model.cat_probs[cat])
    df = pd.DataFrame(out)
    df["annual_inc"] = np.exp(df.pop("annual_inc_log"))
    df["fico_band"] = FICO_BANDS[np.digitize(df["fico_mid"], FICO_EDGES)]
    return df


def _uuid4(n: int, rng: np.random.Generator) -> np.ndarray:
    """n RFC-4122-shaped v4 UUIDs from the stage RNG (uuid.uuid4 is unseedable)."""
    b = rng.integers(0, 256, size=(n, 16), dtype=np.uint8)
    b[:, 6] = (b[:, 6] & 0x0F) | 0x40
    b[:, 8] = (b[:, 8] & 0x3F) | 0x80
    hx = b.tobytes().hex()
    return np.array([f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
                     for h in (hx[i * 32:(i + 1) * 32] for i in range(n))],
                    dtype=object)


def _phones(n: int, rng: np.random.Generator) -> np.ndarray:
    """NANP-shaped numbers: 200-989 area/exchange, any 4-digit line."""
    area = rng.integers(200, 990, size=n)
    exch = rng.integers(200, 990, size=n)
    line = rng.integers(0, 10_000, size=n)
    return np.array([f"{a}-{e}-{l:04d}" for a, e, l in zip(area, exch, line)],
                    dtype=object)


def _typo(s: str, rng: np.random.Generator) -> str:
    """One seeded single-character edit (transpose, drop, or double); always != s."""
    if len(s) < 2:
        return s + s
    i = int(rng.integers(len(s) - 1))
    op = int(rng.integers(3))
    if op == 0 and s[i] != s[i + 1]:  # transpose (no-op on equal chars -> fall through)
        return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    if op <= 1:
        return s[:i] + s[i + 1:]  # drop
    return s[:i] + s[i] + s[i:]  # double


def sample_identity(vocab: IdentityVocab, states: np.ndarray,
                    rng: np.random.Generator) -> pd.DataFrame:
    """Sample one identity per row of states; emails are unique across rows."""
    n = len(states)
    first = rng.choice(vocab.first_names, size=n, p=vocab.first_probs)
    last = rng.choice(vocab.last_names, size=n, p=vocab.last_probs)

    # Emails: name-derived local parts (so duplicates' name/email signals cohere),
    # a free-mail domain, digit suffixes resolving collisions deterministically
    fl, ll = np.char.lower(first.astype(str)), np.char.lower(last.astype(str))
    pattern = rng.integers(0, 4, size=n)
    digits = rng.integers(0, 100, size=n)
    local = np.where(pattern == 0, np.char.add(np.char.add(fl, "."), ll),
             np.where(pattern == 1, np.char.add(fl, ll),
              np.where(pattern == 2, np.char.add(fl.astype("<U1"), ll),
                       np.char.add(np.char.add(fl, ll),
                                   np.char.zfill(digits.astype(str), 2)))))
    domains = rng.choice(vocab.email_domains, size=n)
    email = pd.Series(np.char.add(np.char.add(local, "@"), domains.astype(str)))
    while email.duplicated().any():  # append seeded digits until globally unique
        dup = email.duplicated()
        suffix = rng.integers(0, 1000, size=int(dup.sum())).astype(str)
        loc, _, dom = np.char.partition(email[dup].to_numpy(dtype=str), "@").T
        email[dup] = np.char.add(np.char.add(np.char.add(loc, suffix), "@"), dom)

    # Street/city assembled from Faker's own formats over its vocabularies
    st_num = rng.integers(1, 10_000, size=n).astype(str)
    st_name = rng.choice(np.concatenate([vocab.first_names, vocab.last_names]), size=n)
    st_suff = rng.choice(vocab.street_suffixes, size=n)
    street = np.array([f"{a} {b} {c}" for a, b, c in zip(st_num, st_name, st_suff)],
                      dtype=object)
    city_stem = rng.choice(vocab.first_names, size=n)
    city_pre = rng.choice(vocab.city_prefixes, size=n)
    city_suf = rng.choice(vocab.city_suffixes, size=n)
    cform = rng.integers(0, 4, size=n)
    city = np.select(
        [cform == 0, cform == 1, cform == 2],
        [np.char.add(np.char.add(city_pre.astype(str), " "),
                     np.char.add(city_stem.astype(str), city_suf.astype(str))),
         np.char.add(np.char.add(city_pre.astype(str), " "), city_stem.astype(str)),
         np.char.add(city_stem.astype(str), city_suf.astype(str))],
        default=np.char.add(rng.choice(vocab.last_names, size=n).astype(str),
                            city_suf.astype(str)))

    # Zip codes drawn inside Faker's per-state ranges -> consistent with addr_state
    lo = np.array([vocab.zip_lo[s] for s in states])
    hi = np.array([vocab.zip_hi[s] for s in states])
    zips = lo + (rng.uniform(size=n) * (hi - lo + 1)).astype(int)
    zip_code = np.char.zfill(zips.astype(str), 5)

    return pd.DataFrame({
        "first_name": first, "last_name": last, "email": email.to_numpy(),
        "phone": _phones(n, rng), "street_address": street,
        "city": city.astype(object), "zip_code": zip_code.astype(object),
    })


def _corrupt_duplicates(dups: pd.DataFrame, taken_emails: set[str],
                        rng: np.random.Generator) -> pd.DataFrame:
    """Apply the C7 corruption mix in place; returns dups with a corruption column."""
    kinds = rng.choice(CORRUPTIONS, size=len(dups), p=CORRUPTION_PROBS)
    dups = dups.assign(is_duplicate=True, corruption=kinds)

    nick = np.isin(kinds, ["nickname", "all"])
    dups.loc[nick, "first_name"] = [
        NICKNAMES.get(f, None) or _typo(f, rng)
        for f in dups.loc[nick, "first_name"]]

    typo = np.isin(kinds, ["email_typo", "all"])
    new_emails = []
    for e in dups.loc[typo, "email"]:
        loc, _, dom = e.partition("@")
        cand = _typo(loc, rng) + "@" + dom
        while cand in taken_emails:  # astronomically rare; keep exactness anyway
            cand = _typo(loc, rng) + str(rng.integers(10)) + "@" + dom
        taken_emails.add(cand)
        new_emails.append(cand)
    dups.loc[typo, "email"] = new_emails

    phone = np.isin(kinds, ["new_phone", "all"])
    dups.loc[phone, "phone"] = _phones(int(phone.sum()), rng)
    return dups


def build_population(model: CreditModel, vocab: IdentityVocab, n: int,
                     duplicate_rate: float, rng: np.random.Generator) -> pd.DataFrame:
    """The full consumer table: exactly n records, ~duplicate_rate of them
    duplicate records sharing a base person's consumer_key (design Section 2.3).

    Sources for duplicates are drawn with replacement, so a few persons carry
    three or more records — real duplicate flooding is not pairwise-only.
    """
    n_dup = int(round(n * duplicate_rate))
    n_base = n - n_dup

    credit = sample_credit(model, n_base, rng)
    ident = sample_identity(vocab, credit["addr_state"].to_numpy(), rng)
    base = pd.concat([ident, credit], axis=1)
    base.insert(0, "consumer_key", _uuid4(n_base, rng))
    base.insert(1, "is_duplicate", False)
    base.insert(2, "corruption", pd.NA)

    # Duplicates: same person, verbatim credit profile, corrupted identity fields
    src = rng.integers(0, n_base, size=n_dup)
    dups = _corrupt_duplicates(base.iloc[src].drop(columns="corruption"),
                               set(base["email"]), rng)

    pop = pd.concat([base, dups], ignore_index=True)
    # Per-record key (leads reference a specific identity record); independent of
    # consumer_key so no silo-visible id can leak the hidden person key
    pop.insert(0, "consumer_record_id", _uuid4(len(pop), rng))
    # Shuffle so duplicate records are not positionally clustered downstream
    return pop.iloc[rng.permutation(len(pop))].reset_index(drop=True)
