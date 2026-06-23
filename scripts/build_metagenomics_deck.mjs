import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(
  "/Users/krishnaiitm/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json",
);
const { Presentation, PresentationFile } = await import(require.resolve("@oai/artifact-tool"));

const W = 1280;
const H = 720;
const ROOT = "/private/tmp/codex-presentations/metagenomics_full_deck";
const OUT = `${ROOT}/out/metagenomics_pipeline_complete.pptx`;
const PREVIEW = `${ROOT}/tmp/preview`;
const LAYOUT = `${ROOT}/tmp/layout`;
const QA = `${ROOT}/tmp/qa`;

await fs.mkdir(path.dirname(OUT), { recursive: true });
await fs.mkdir(PREVIEW, { recursive: true });
await fs.mkdir(LAYOUT, { recursive: true });
await fs.mkdir(QA, { recursive: true });

const C = {
  bg: "#050505",
  panel: "#111111",
  text: "#F8FAFC",
  muted: "#CBD5E1",
  sub: "#94A3B8",
  line: "#334155",
  cyan: "#38BDF8",
  green: "#22C55E",
  amber: "#F59E0B",
  purple: "#A78BFA",
  orange: "#F97316",
  red: "#EF4444",
};

const deck = Presentation.create({ slideSize: { width: W, height: H } });
let slideNo = 1;

function text(slide, value, left, top, width, height, opts = {}) {
  const box = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  box.text = value;
  box.text.style = {
    fontFace: opts.font ?? "Aptos",
    fontSize: opts.size ?? 22,
    bold: opts.bold ?? false,
    color: opts.color ?? C.text,
    alignment: opts.align ?? "left",
  };
  return box;
}

function rect(slide, left, top, width, height, fill, line = fill) {
  return slide.shapes.add({
    geometry: "rect",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: 1 },
  });
}

function round(slide, left, top, width, height, fill = C.panel, line = C.line) {
  return slide.shapes.add({
    geometry: "roundRect",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: 1 },
    borderRadius: "rounded-lg",
  });
}

function footer(slide, n) {
  text(slide, "Metagenomics ASV + Taxonomy Pipeline", 60, 674, 520, 18, {
    size: 10,
    color: "#64748B",
  });
  text(slide, String(n).padStart(2, "0"), 1170, 672, 50, 20, {
    size: 12,
    bold: true,
    color: "#64748B",
    align: "right",
  });
}

function title(slide, value, kicker = "") {
  if (kicker) {
    text(slide, kicker.toUpperCase(), 60, 34, 760, 24, {
      size: 12,
      bold: true,
      color: C.cyan,
    });
  }
  text(slide, value, 60, 58, 980, 58, {
    size: 36,
    bold: true,
    color: C.text,
    font: "Aptos Display",
  });
  rect(slide, 60, 124, 140, 4, C.cyan);
}

function base(value, kicker = "") {
  const slide = deck.slides.add();
  slide.background.fill = C.bg;
  title(slide, value, kicker);
  footer(slide, slideNo++);
  return slide;
}

function bullet(slide, items, left, top, width, opts = {}) {
  const size = opts.size ?? 21;
  const gap = opts.gap ?? 48;
  items.forEach((item, i) => {
    round(slide, left, top + i * gap + 9, 10, 10, opts.dot ?? C.cyan, opts.dot ?? C.cyan);
    text(slide, item, left + 24, top + i * gap, width - 24, gap + 4, {
      size,
      color: opts.color ?? C.text,
      bold: opts.bold ?? false,
    });
  });
}

function card(slide, heading, body, left, top, width, height, accent = C.cyan) {
  round(slide, left, top, width, height, C.panel, "#273142");
  rect(slide, left, top, 6, height, accent);
  text(slide, heading, left + 22, top + 18, width - 44, 28, {
    size: 20,
    bold: true,
  });
  text(slide, body, left + 22, top + 54, width - 44, height - 64, {
    size: 16,
    color: C.muted,
  });
}

function pill(slide, label, left, top, width, color = C.cyan) {
  round(slide, left, top, width, 34, "#0B1220", color);
  text(slide, label, left, top + 7, width, 18, {
    size: 13,
    bold: true,
    color,
    align: "center",
  });
}

function arrow(slide, x1, y1, x2, y2, color = C.sub) {
  const dx = x2 - x1;
  rect(slide, x1, y1 - 2, dx, 4, color);
}

{
  const s = deck.slides.add();
  s.background.fill = C.bg;
  text(s, "Metagenomics Pipeline for 16S rRNA and ITS-1", 70, 94, 980, 150, {
    size: 54,
    bold: true,
    font: "Aptos Display",
  });
  text(
    s,
    "Transparent ASV generation, multi-database taxonomy assignment, and auditable outputs",
    74,
    262,
    900,
    72,
    { size: 25, color: C.muted },
  );
  pill(s, "DADA2", 74, 370, 120, C.green);
  pill(s, "FastAPI", 210, 370, 130, C.cyan);
  pill(s, "SILVA / RDP / Greengenes2", 360, 370, 260, C.purple);
  text(s, "Krishna Karthikeyan", 74, 560, 420, 28, { size: 24, bold: true });
  text(s, "IIT Madras", 74, 596, 280, 24, { size: 18, color: C.sub });
  footer(s, slideNo++);
}

{
  const s = base("Project Objective", "Objective");
  bullet(
    s,
    [
      "Create an easily modifiable pipeline that reproduces the core metagenomics functions required from DRAGEN-like workflows.",
      "Keep every internal step visible: filtering, denoising, merging, ASV counts, taxonomy assignment, and logs.",
      "Support scientific interpretation by exposing intermediate evidence rather than returning only a final label.",
      "Make the code extensible for 16S, ITS, alternate databases, and future pre-processing steps.",
    ],
    80,
    170,
    1050,
    { size: 23, gap: 72 },
  );
}

{
  const s = base("Why Build a Transparent Pipeline?", "Motivation");
  card(s, "Scientific confidence", "Claims about species or genera should be traceable back to reads, ASVs, database assignment, and confidence thresholds.", 70, 170, 340, 210, C.green);
  card(s, "Modifiability", "Filtering thresholds, trimming rules, database choices, bootstrap thresholds, and output formats can be changed locally.", 470, 170, 340, 210, C.cyan);
  card(s, "Operational visibility", "Failures are diagnosable: for example, all-read loss can be traced to R2 ambiguous bases and maxN=0.", 870, 170, 340, 210, C.orange);
  bullet(s, ["Goal: not a black box, but a reproducible workflow that can be inspected, rerun, and defended.", "Design principle: preserve raw inputs, manifests, intermediate files, final outputs, and logs per job."], 100, 455, 1050, { size: 22, gap: 60, dot: C.purple });
}

{
  const s = base("Capabilities of the Software", "Capabilities");
  bullet(
    s,
    [
      "Upload paired-end or single-end FASTQ / FASTQ.GZ files",
      "Run DADA2 filtering, denoising, merging, and chimera removal",
      "Generate ASV FASTA files and read count tables",
      "Assign taxonomy using SILVA, RDP, and Greengenes2 for 16S",
      "Produce final long-format taxonomy CSV outputs",
      "Expose job manifests, status files, logs, and tmp outputs",
      "Resume from filtered/high-quality intermediate FASTQs",
      "Adjust settings for problematic reads or low-quality data",
    ],
    80,
    160,
    1080,
    { size: 20, gap: 54, dot: C.green },
  );
}

{
  const s = base("End-to-End Architecture", "Architecture");
  const xs = [60, 310, 590, 875, 1085];
  const y = 215;
  card(s, "HTML UI", "Upload form\nJob status page\nDownload links", xs[0], y, 190, 155, C.cyan);
  card(s, "Python FastAPI", "web_app.py\nmanifest.json\nstatus.json", xs[1], y, 210, 155, C.cyan);
  card(s, "R / DADA2", "filterAndTrim\nlearnErrors\ndada + merge", xs[2], y, 220, 155, C.green);
  card(s, "Python Classifier", "asv_classifier.py\nassign_taxonomy.R\nconsensus CSV", xs[3], y, 190, 155, C.purple);
  card(s, "Outputs", "ASV FASTA\nCounts CSV\nTaxonomy long CSV", xs[4], y, 150, 155, C.amber);
  arrow(s, 260, y + 78, 298, y + 78);
  arrow(s, 520, y + 78, 578, y + 78);
  arrow(s, 810, y + 78, 862, y + 78);
  arrow(s, 1065, y + 78, 1078, y + 78);
  text(s, "Job workspace: jobs/{job_id}/inputs + outputs + tmp + logs", 160, 465, 920, 38, {
    size: 24,
    bold: true,
    align: "center",
  });
}

{
  const s = base("Job Workspace and Output Contract", "Implementation");
  const cols = [80, 360, 640, 920];
  ["inputs/", "outputs/", "tmp/", "status + logs"].forEach((heading, i) =>
    card(
      s,
      heading,
      [
        "Uploaded FASTQ files\nSafe filenames\nRaw data retained",
        "filtered FASTQs\nasvs.fasta\nasv_counts.csv\ndada2_summary.csv\ntaxonomy_long.csv",
        "assign_taxonomy JSON/CSV\nReusable intermediate state\nmin_boot reruns",
        "status.json\ndada2.log\nerror.log\ntransparent failure trace",
      ][i],
      cols[i],
      180,
      220,
      280,
      [C.cyan, C.green, C.purple, C.amber][i],
    ),
  );
  text(s, "Every job is isolated, reproducible, and inspectable after execution.", 160, 525, 960, 48, { size: 25, bold: true, align: "center", color: C.muted });
}

{
  const s = base("Algorithm: ASV Generation", "DADA2");
  const steps = ["Quality filtering", "Error learning", "Dereplication", "Denoising", "Paired-end merging", "Chimera removal", "ASV table"];
  const descriptions = ["Remove low-quality reads", "Estimate error rates", "Collapse identical reads", "Infer exact variants", "Reconstruct amplicon", "Remove PCR artifacts", "FASTA + counts"];
  const x0 = 70;
  const y0 = 230;
  steps.forEach((step, i) => {
    card(s, step, descriptions[i], x0 + i * 170, y0, 145, 140, [C.cyan, C.green, C.green, C.purple, C.purple, C.orange, C.amber][i]);
    if (i < steps.length - 1) arrow(s, x0 + i * 170 + 146, y0 + 70, x0 + (i + 1) * 170 - 8, y0 + 70);
  });
  bullet(s, ["ASVs preserve single-nucleotide resolution and avoid arbitrary OTU clustering thresholds.", "The output sequence set is inferred from data and an explicit sequencing error model."], 95, 485, 1060, { size: 22, gap: 58, dot: C.green });
}

{
  const s = base("Math Behind Filtering", "ASV Algorithm");
  text(s, "Expected errors", 80, 160, 400, 32, { size: 28, bold: true, color: C.cyan });
  text(s, "EE(read) = sum_i 10^(-Q_i / 10)", 100, 220, 640, 48, { size: 34, bold: true });
  bullet(s, ["Q_i is the Phred quality score at base i.", "A read is retained only if EE <= maxEE.", "Ambiguous bases are rejected using maxN = 0.", "For paired reads, either mate failing removes the pair."], 100, 315, 640, { size: 22, gap: 56, dot: C.cyan });
  card(s, "Practical example", "S11 R2 had N bases at early positions in every read. With maxN=0, all pairs were removed. Trimming R2 by 40 bases restored 161,136 filtered pairs.", 800, 200, 360, 260, C.orange);
}

{
  const s = base("Math Behind Error Learning and Dereplication", "ASV Algorithm");
  card(s, "Error model", "DADA2 estimates P(observed base | true base, quality score). This model is learned from the dataset rather than assumed fixed.", 80, 170, 480, 185, C.green);
  card(s, "Dereplication", "Identical reads are collapsed: sequence_i -> abundance n_i. Computation is reduced while abundance evidence is preserved.", 640, 170, 480, 185, C.cyan);
  text(s, "Core idea", 80, 430, 220, 34, { size: 26, bold: true, color: C.purple });
  text(s, "The algorithm separates biological variants from the distribution of errors expected at each quality score.", 100, 485, 960, 56, { size: 27 });
}

{
  const s = base("Math Behind Denoising", "ASV Algorithm");
  text(s, "DADA2 evaluates whether a sequence is too abundant or too different to be explained as an error from an existing parent sequence.", 80, 160, 1060, 60, { size: 24, color: C.muted });
  text(s, "Keep sequence s if:", 110, 270, 340, 34, { size: 26, bold: true, color: C.cyan });
  text(s, "P(s | parent ASV, error model) is sufficiently small", 160, 335, 850, 44, { size: 32, bold: true });
  bullet(s, ["If the sequence is explainable by error, it is absorbed into the parent ASV.", "If not explainable, it becomes a new exact sequence variant.", "Pooling can increase sensitivity but increases runtime; standard mode uses pool = FALSE."], 120, 440, 990, { size: 22, gap: 60, dot: C.purple });
}

{
  const s = base("Merging and Chimera Removal", "ASV Algorithm");
  card(s, "Paired-end merge", "Forward and reverse reads are aligned in their overlap region. A merge is accepted when overlap >= minOverlap and mismatches <= maxMismatch.", 80, 165, 500, 190, C.green);
  card(s, "Chimera detection", "A sequence is flagged if it can be reconstructed as prefix(parent_1) + suffix(parent_2) from more abundant ASVs.", 700, 165, 500, 190, C.orange);
  text(s, "Final ASV abundance", 80, 440, 390, 34, { size: 26, bold: true, color: C.cyan });
  text(s, "count(ASV_j) = number of reads assigned to exact inferred variant j", 115, 505, 900, 46, { size: 30, bold: true });
}

{
  const s = base("Algorithm: Assign Taxonomy", "Taxonomy");
  card(s, "Input", "ASV sequences from DADA2: asvs.fasta + asv_counts.csv", 80, 180, 330, 160, C.green);
  card(s, "Classifier", "DADA2 assignTaxonomy via assign_taxonomy.R", 475, 180, 330, 160, C.purple);
  card(s, "Reference DBs", "SILVA, RDP, Greengenes2 for 16S", 870, 180, 330, 160, C.amber);
  arrow(s, 410, 260, 470, 260);
  arrow(s, 805, 260, 865, 260);
  bullet(s, ["Each ASV is classified independently against each database.", "The final long table keeps database-specific results instead of hiding disagreements.", "min_boot=0 retains low-confidence lower ranks for interpretation; confidence remains visible in labels."], 120, 430, 1000, { size: 22, gap: 58, dot: C.purple });
}

{
  const s = base("Math Behind Naive Bayes Taxonomy", "Taxonomy");
  text(s, "For a query ASV represented by k-mers k_1...k_n:", 80, 160, 760, 34, { size: 24, color: C.muted });
  text(s, "score(taxon) proportional to P(taxon) * product_i P(k_i | taxon)", 105, 230, 1030, 48, { size: 31, bold: true });
  bullet(s, ["The naive assumption treats k-mer evidence as conditionally independent given a taxon.", "Bootstrapping repeatedly resamples evidence to estimate assignment confidence.", "Ranks below the bootstrap threshold are blanked; using min_boot=0 preserves more tentative labels."], 110, 350, 990, { size: 23, gap: 62, dot: C.cyan });
}

{
  const s = base("Multi-Database Comparison and Consensus", "Taxonomy");
  card(s, "SILVA", "Large curated 16S reference; broad coverage, often slower.", 80, 175, 310, 170, C.green);
  card(s, "RDP", "Classic ribosomal database; usually faster and conservative.", 485, 175, 310, 170, C.cyan);
  card(s, "Greengenes2", "Modern phylogeny-aware reference; useful cross-check.", 890, 175, 310, 170, C.purple);
  text(s, "Consensus rule used for 16S", 110, 440, 420, 32, { size: 26, bold: true, color: C.amber });
  bullet(s, ["For each rank, accept agreement when at least two databases support the same label.", "Stop consensus at the first rank without agreement.", "Database-specific rows remain in taxonomy_long.csv for flexible interpretation."], 135, 500, 980, { size: 22, gap: 50, dot: C.amber });
}

{
  const s = base("Implementation Modules", "Software");
  const modules = [
    ["web_app.py", "FastAPI routes, uploads, job creation, status pages"],
    ["dada2_runner.py", "Manifest creation and Rscript execution"],
    ["dada2_pipeline.R", "Full DADA2 run from raw FASTQ"],
    ["dada2_resume_filtered.R", "Resume from filtered/high-quality FASTQs"],
    ["asv_classifier.py", "Read ASVs, run assignTaxonomy, write long CSV"],
    ["assign_taxonomy.R", "DADA2 assignTaxonomy wrapper"],
    ["config/*.yaml", "Database paths, marker-specific settings"],
    ["taxonomy_pipeline/*.py", "Models, config loading, utilities"],
  ];
  modules.forEach((m, i) => card(s, m[0], m[1], 80 + (i % 2) * 560, 155 + Math.floor(i / 2) * 105, 500, 78, [C.cyan, C.cyan, C.green, C.green, C.purple, C.purple, C.amber, C.amber][i]));
}

{
  const s = base("Configuration Modes", "Software");
  card(s, "Standard mode", "Uses base DADA2 parameters: maxN=0, maxEE=[5,5], minOverlap=12, pool=FALSE by R default.", 80, 180, 500, 210, C.cyan);
  card(s, "Relaxed mode", "Loosens filtering/merging and turns on sensitivity settings: maxEE=[10,10], minOverlap=6, pool=TRUE, omegaA=1e-20.", 700, 180, 500, 210, C.orange);
  card(s, "Manual rescue mode", "For sample-specific read defects, edit manifest trimLeft or resume from filtered FASTQs without rerunning all earlier steps.", 390, 455, 500, 145, C.green);
}

{
  const s = base("Development History: From Prototype to Pipeline", "What was tried");
  card(s, "First local app", "FastAPI + HTML interface around an existing V3-V4 classifier and local database files.", 70, 165, 340, 190, C.cyan);
  card(s, "Three input routes", "FASTA direct classification, FASTQ via DADA2 to ASVs, and future-ready POD5 via Dorado to FASTQ.", 470, 165, 340, 190, C.green);
  card(s, "Current mature path", "The final project shifted toward transparent DADA2 ASV generation and multi-database taxonomy assignment.", 870, 165, 340, 190, C.purple);
  bullet(s, ["The database artifacts were treated as fixed inputs, not rebuilt.", "Dorado/POD5 support was designed as optional: clear failure if Dorado is not installed.", "The workflow evolved from a classifier wrapper into a more auditable metagenomics pipeline."], 105, 430, 1040, { size: 22, gap: 58, dot: C.amber });
}

{
  const s = base("FASTQ Visual QC Work", "What was tried");
  card(s, "QC report generator", "A dependency-light Python script parsed FASTQ files and generated an HTML report with inline visualizations.", 80, 165, 500, 180, C.cyan);
  card(s, "Visualizations", "Per-base quality, GC distribution, base composition, N content, prefix summaries, tile counts, duplication and overlap estimates.", 700, 165, 500, 180, C.green);
  text(s, "Example QC headline from earlier paired data", 100, 420, 760, 34, { size: 26, bold: true, color: C.amber });
  bullet(s, ["R1: 103,773 reads, 251 bp each, GC about 58.2%, mean Q about 35.6.", "R2: 103,773 reads, 251 bp each, GC about 57.1%, mean Q about 34.7.", "This QC layer made read defects visible before running expensive downstream tools."], 125, 485, 1000, { size: 21, gap: 48, dot: C.amber });
}

{
  const s = base("Exploratory Sequence Clustering", "What was tried");
  card(s, "Method", "Collapsed duplicate paired signatures, then clustered representative sequences using identity and k-mer similarity.", 80, 170, 500, 190, C.purple);
  card(s, "Practical tuning", "An exhaustive all-unique comparison was too slow, so the default became an abundance-capped top-10k exploratory run.", 700, 170, 500, 190, C.orange);
  bullet(s, ["Signature used: R1 + spacer + reverse_complement(R2).", "Default thresholds: 97% positional identity and 90% k-mer similarity.", "Explicit k=8 run produced 1,449 clusters from the top 10,000 unique paired signatures.", "Largest cluster contained 55,375 reads, supporting a dominant sequence signal."], 110, 430, 1040, { size: 21, gap: 48, dot: C.cyan });
}

{
  const s = base("Earlier 18S Exploration", "What was tried");
  card(s, "DADA2 result", "One paired-end 18S sample retained 93,187 non-chimeric merged reads from 103,773 input pairs and produced 9 final ASVs.", 80, 165, 500, 205, C.green);
  card(s, "Taxonomy lesson", "Local SILVA exact/best-window matching was weak; NCBI BLAST produced stronger interpretability for the dominant ASVs.", 700, 165, 500, 205, C.amber);
  bullet(s, ["ASV1 dominated the table with 77,612 reads, about 83.29% of non-chimeric reads.", "BLAST suggested the dominant signal was closest to Neoscytalidium hyalinum / related Neoscytalidium species.", "This earlier work informed the final emphasis on validation, database choice, and transparent evidence."], 105, 440, 1040, { size: 21, gap: 55, dot: C.purple });
}

{
  const s = base("Reporting Honesty: Placeholder Output Removed", "What failed");
  bullet(s, ["An early no-dependency local runner generated placeholder taxonomy so the UI could show downloadable files.", "That was useful for testing the app shell but unacceptable because it looked like real biology.", "The report path was corrected to stop fabricating taxa: empty taxonomy table, real FASTQ QC, and clear 'taxonomy not run' status.", "This became a project principle: never hide missing tools/databases behind fake biological output."], 90, 165, 1040, { size: 23, gap: 72, dot: C.red });
}

{
  const s = base("Optimization Attempts and Decisions", "What was tried");
  card(s, "Classifier bottleneck", "The early V3-V4 classifier spent most time in pure-Python edit-distance alignment after k-mer candidate lookup.", 80, 170, 500, 175, C.orange);
  card(s, "Rapidfuzz experiment", "A compiled edit-distance option was considered, then reverted to avoid unapproved dependency changes.", 700, 170, 500, 175, C.cyan);
  card(s, "Final direction", "For this version, optimization focused on removing the worst identity-scoring bottleneck and preserving transparent DADA2/taxonomy outputs.", 390, 420, 500, 150, C.green);
}

{
  const s = base("Failure Case: All Reads Removed", "Validation");
  text(s, "Observed failure", 80, 160, 360, 34, { size: 28, bold: true, color: C.orange });
  bullet(s, ["S11 raw R2 contained N bases in every read at early positions.", "Current filter used maxN = 0, so any ambiguous mate caused pair removal.", "DADA2 wrote: No reads passed the filter."], 100, 230, 620, { size: 23, gap: 70, dot: C.orange });
  card(s, "Root cause", "Not a FASTQ vs FASTQ.GZ problem. The plain FASTQ opened correctly; the failure was biological/quality content in R2 plus strict maxN filtering.", 760, 230, 360, 220, C.red);
}

{
  const s = base("Fix: R2 Trim and Filtered Resume", "Validation");
  card(s, "Change", "Set trimLeft = [0,40] for S11 so the early ambiguous R2 region is removed before maxN filtering.", 80, 165, 500, 170, C.green);
  card(s, "Result", "Filtered read pairs recovered: 161,136. R1 and R2 filtered FASTQs passed gzip integrity and line-count checks.", 700, 165, 500, 170, C.cyan);
  card(s, "Resume strategy", "dada2_resume_filtered.R starts from outputs/filtered/R1_filtered.fastq.gz and R2_filtered.fastq.gz to avoid repeating filtering.", 390, 420, 500, 160, C.purple);
}

{
  const s = base("Runtime Issue: Identity Scoring Removed", "Validation");
  bullet(s, ["Original classifier added a custom identity score by scanning each ASV against references for the assigned taxon.", "For thousands of ASVs and large databases, this became a pure-Python bottleneck.", "The bloated identity pass was removed; the identity column is retained blank for CSV compatibility.", "Taxonomy now writes the long table directly after assignTaxonomy outputs are ready."], 90, 165, 1040, { size: 23, gap: 72, dot: C.orange });
}

{
  const s = base("Validation Evidence from Runs", "Results");
  const data = [
    ["Original S19", "3,067 ASVs", "9,201 taxonomy rows", "Completed"],
    ["Trimmed S11", "6,725 ASVs", "min_boot=0 running", "DADA2 complete"],
    ["Highqual normal S19", "1,095 ASVs", "min_boot=0 running", "DADA2 complete"],
    ["Highqual normal S11", "3,422 ASVs", "min_boot=0 running", "DADA2 complete"],
  ];
  data.forEach((d, i) => card(s, d[0], `${d[1]}\n${d[2]}\n${d[3]}`, 80 + (i % 2) * 560, 165 + Math.floor(i / 2) * 190, 500, 145, [C.green, C.orange, C.cyan, C.purple][i]));
  text(s, "Counts are from current job outputs at deck-generation time.", 170, 595, 940, 26, { size: 16, color: C.sub, align: "center" });
}

{
  const s = base("Final Output Format", "Outputs");
  card(s, "ASV FASTA", ">ASV_1\nACTG...", 80, 160, 310, 130, C.green);
  card(s, "ASV count table", "asv_id, reads, sequence", 485, 160, 310, 130, C.cyan);
  card(s, "taxonomy_long.csv", "One row per ASV per database", 890, 160, 310, 130, C.amber);
  text(s, "Long-format taxonomy schema", 80, 365, 520, 32, { size: 26, bold: true, color: C.purple });
  bullet(s, ["job_id, asv_id, sequence, reads, percent_abundance", "marker, database, kingdom...species", "match_type, identity, consensus_taxonomy"], 105, 430, 1000, { size: 22, gap: 54, dot: C.purple });
}

{
  const s = base("Limitations", "Critical Appraisal");
  bullet(s, ["Runtime can be high: DADA2 error learning and large database assignTaxonomy are CPU-bound.", "Reference database choice affects depth and confidence of classification.", "Low-confidence taxonomy must be interpreted carefully, especially with min_boot=0.", "Amplicon sequencing cannot always resolve true species when marker regions are shared.", "Pipeline depends on curated database files being present locally and correctly versioned."], 90, 165, 1060, { size: 23, gap: 70, dot: C.red });
}

{
  const s = base("Future Improvements", "Roadmap");
  card(s, "Vector / k-mer index search", "Pre-build searchable k-mer tables or vector indexes to accelerate nearest reference lookup and database comparisons.", 80, 170, 330, 220, C.cyan);
  card(s, "GPU-aware acceleration", "Explore GPU acceleration where algorithms support it; DADA2 itself currently runs on CPU threads.", 475, 170, 330, 220, C.green);
  card(s, "Workflow polish", "Add resumable background job management, clearer progress logs, and user-selectable min_boot / trimming controls.", 870, 170, 330, 220, C.amber);
  bullet(s, ["Add demultiplexing and POD5 conversion hooks where appropriate.", "Add database version reporting and reproducibility metadata to final outputs."], 120, 470, 980, { size: 22, gap: 55, dot: C.purple });
}

{
  const s = base("Conclusion", "Summary");
  text(s, "The pipeline converts raw amplicon reads into transparent, inspectable ASV and taxonomy outputs.", 90, 170, 1040, 70, { size: 32, bold: true, align: "center" });
  bullet(s, ["DADA2 provides exact sequence variants rather than coarse OTU clusters.", "Multi-database taxonomy keeps SILVA, RDP, and Greengenes2 evidence visible.", "Failure analysis is practical because every job stores manifests, logs, and intermediate files.", "The result is a modifiable research pipeline whose assumptions can be inspected and defended."], 120, 300, 980, { size: 24, gap: 65, dot: C.green });
}

{
  const s = base("References", "Sources");
  bullet(s, ["Callahan et al. DADA2: High-resolution sample inference from Illumina amplicon data. Nature Methods, 2016.", "DADA2 package documentation: filterAndTrim, learnErrors, dada, mergePairs, assignTaxonomy.", "SILVA ribosomal RNA database, RDP classifier resources, Greengenes2 reference database.", "Project source code, generated job artifacts, and earlier Codex project logs supplied as context."], 90, 170, 1060, { size: 22, gap: 74, dot: C.cyan });
  text(s, "Note: local file paths and run folders were used for provenance but are not required to interpret the deck.", 100, 610, 1040, 34, { size: 16, color: C.sub, align: "center" });
}

for (let i = 0; i < deck.slides.items.length; i += 1) {
  const slide = deck.slides.items[i];
  const stem = `slide-${String(i + 1).padStart(2, "0")}`;
  const png = await deck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(PREVIEW, `${stem}.png`), new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(path.join(LAYOUT, `${stem}.layout.json`), await layout.text());
}

const montage = await deck.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(`${PREVIEW}/montage.webp`, new Uint8Array(await montage.arrayBuffer()));

const pptx = await PresentationFile.exportPptx(deck);
await pptx.save(OUT);

await fs.writeFile(
  `${QA}/visual-qa.txt`,
  `Rendered ${deck.slides.items.length} slides and a montage. Source PPTX inspection failed on one embedded source object, so the final deck was generated in a matching dark high-contrast style with editable native objects.\n`,
);

console.log(JSON.stringify({ slides: deck.slides.items.length, pptx: OUT, montage: `${PREVIEW}/montage.webp` }, null, 2));
