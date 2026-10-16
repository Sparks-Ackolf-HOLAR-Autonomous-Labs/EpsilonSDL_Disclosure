# DFT check of the vacancy-hop barriers: registered predictions

Registered 2026-10-10, before any QE NEB output exists. The MACE-MP-0 barriers come from
`../results/vacancy_neb.jsonl` (4x4 cells); the DFT runs use the 3x3 cells described in
`make_neb_inputs.py` (PBE, GBRV USPP, 40/320 Ry, 3x3x1 k-points, 5-image climbing-image NEB).

Compounds (MACE hop barrier, eV): WS2 2H 1.01, MoS2 2H 0.90, HfS2 1T 0.86, TiS2 1T 0.72,
ZrTe2 1T 0.48, TiTe2 1T 0.40, MoS2 1T 0.23. MoS2 1T is a dynamically unstable host
(it distorts to 1T'), kept as the low end and reported separately.
"Stable set" = the other six.

| Id | Prediction | Pass condition |
| --- | --- | --- |
| N1 | MACE softens the energy surface | DFT barrier > MACE barrier in all six of the stable set |
| N2 | The literature anchor is reproduced | MoS2 2H DFT barrier in 2.0 to 2.6 eV (published PBE about 2.3 eV, Komsa et al. 2012) |
| N3 | MACE ranks the compounds correctly | Spearman rank correlation MACE vs DFT >= 0.6 over all seven |
| N4 | The spread between compounds is preserved at DFT level (the decisive test for the kMC rung) | max minus min DFT barrier over the stable set >= 0.3 eV |
| N5 | The kMC cost spread is preserved | at the same 1000 K anneal, the kMC event-count ratio between the fastest and slowest stable compound, computed from the DFT barriers, >= 100 |

Decision rule: if N4 and N5 pass, the kMC rung in the twin uses DFT barriers (MACE barriers
shifted per compound by the measured DFT correction for the compounds not computed) and the
provisional surface run stands in shape. If N4 fails, the kMC slope on the training axis is a
force-field artefact and is withdrawn.

Collection: `collect_neb.sh` (copies `results/*.json` and the `*.neb.out` files from scratch
into `results_dft/`), then `analyze_neb.py` grades N1 to N5.
