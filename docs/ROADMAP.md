# Metagenomics Pipeline Roadmap

## Recommended Next Step

Add sequence identity and nearest-reference validation for every ASV. The current
pipeline already runs DADA2, assigns taxonomy across configured databases, stores
completed jobs, and can generate a PDF report. The next highest-value improvement
is making each taxonomic call easier to verify.

## Priority 1: Closest-Match Validation

- Search each ASV against the configured reference FASTA files.
- Report the top 5 closest matches per ASV.
- Include percent identity, mismatch count, database name, reference header, and
  reference taxonomy when available.
- Add a separate `assign_species()` function for exact or best species-level
  matching.
- Keep the DADA2 consensus taxonomy, but add nearest-match evidence beside it.

## Priority 2: NTC Background Control

- Compare sample ASVs against no-template-control jobs.
- Flag exact ASV sequence matches also seen in the NTC.
- Include read counts, percent abundance, and sample-to-NTC abundance ratios.
- Surface likely contaminants in CSV and report outputs.

## Priority 3: Multi-Sample Summary

- Aggregate multiple completed jobs into one sample-by-ASV and sample-by-taxon
  table.
- Keep ASV sequence as the stable join key across samples.
- Add per-sample totals, relative abundance, and contaminant flags.

## Priority 4: Report And Visualization Upgrades

- Extend the PDF report with closest-match evidence and NTC flags.
- Add interactive taxonomy visualizations such as Krona after the classification
  evidence is richer.
- Add a progress bar to the web UI for long-running DADA2 and classification
  jobs.

## Later Optimization

- Pre-build k-mer or minimizer indexes for reference databases if nearest-match
  search becomes slow.
- Consider GPU or vectorized acceleration only after profiling shows database
  search is the bottleneck.
