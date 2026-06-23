suppressPackageStartupMessages({
  library(dada2)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  stop("Usage: Rscript dada2_resume_filtered.R manifest.json")
}

manifest <- fromJSON(args[[1]], simplifyVector = FALSE)
outdir <- manifest$output_dir
params <- manifest$params
filtered_dir <- file.path(outdir, "filtered")

get_param <- function(name, default) {
  value <- params[[name]]
  if (is.null(value)) default else value
}

count_fastq_records <- function(path) {
  con <- gzfile(path, "rt")
  on.exit(close(con), add = TRUE)
  lines <- 0L
  repeat {
    chunk <- readLines(con, n = 1000000L, warn = FALSE)
    if (length(chunk) == 0) {
      break
    }
    lines <- lines + length(chunk)
  }
  as.integer(lines / 4L)
}

remove_chimeras <- function(seqtab) {
  method <- get_param("chimeraMethod", "consensus")
  if (identical(method, "none")) {
    return(seqtab)
  }
  removeBimeraDenovo(seqtab, method = method, multithread = TRUE, verbose = TRUE)
}

write_outputs <- function(seqtab, summary_rows) {
  asv_seqs <- colnames(seqtab)
  if (is.null(asv_seqs) || length(asv_seqs) == 0) {
    stop("DADA2 produced zero ASVs")
  }
  asv_ids <- paste0("ASV_", seq_along(asv_seqs))
  names(asv_seqs) <- asv_ids

  fasta_con <- file(manifest$asv_fasta, "w")
  on.exit(close(fasta_con), add = TRUE)
  for (asv_id in asv_ids) {
    writeLines(paste0(">", asv_id), fasta_con)
    writeLines(asv_seqs[[asv_id]], fasta_con)
  }

  counts <- colSums(seqtab)
  count_table <- data.frame(asv_id = names(asv_seqs), reads = as.integer(counts), sequence = asv_seqs)
  write.csv(count_table, manifest$count_table, row.names = FALSE, quote = FALSE)
  write.csv(summary_rows, manifest$summary_table, row.names = FALSE, quote = FALSE)
}

if (manifest$read_mode != "paired") {
  stop("Filtered resume currently supports paired-end runs only.")
}

filt_f <- file.path(filtered_dir, "R1_filtered.fastq.gz")
filt_r <- file.path(filtered_dir, "R2_filtered.fastq.gz")
if (!file.exists(filt_f) || !file.exists(filt_r)) {
  stop("Filtered FASTQ files are missing. Expected R1_filtered.fastq.gz and R2_filtered.fastq.gz.")
}

reads_f <- count_fastq_records(filt_f)
reads_r <- count_fastq_records(filt_r)
if (reads_f != reads_r) {
  stop(paste("Filtered read counts differ:", reads_f, "R1 reads vs", reads_r, "R2 reads"))
}

err_f <- learnErrors(filt_f, multithread = TRUE, nbases = get_param("nbases", 1e8))
err_r <- learnErrors(filt_r, multithread = TRUE, nbases = get_param("nbases", 1e8))
derep_f <- derepFastq(filt_f)
derep_r <- derepFastq(filt_r)
dada_f <- dada(
  derep_f,
  err = err_f,
  multithread = TRUE,
  pool = get_param("pool", FALSE),
  OMEGA_A = get_param("omegaA", 1e-40),
  BAND_SIZE = get_param("bandSize", 16)
)
dada_r <- dada(
  derep_r,
  err = err_r,
  multithread = TRUE,
  pool = get_param("pool", FALSE),
  OMEGA_A = get_param("omegaA", 1e-40),
  BAND_SIZE = get_param("bandSize", 16)
)
mergers <- mergePairs(
  dada_f,
  derep_f,
  dada_r,
  derep_r,
  minOverlap = get_param("minOverlap", 12),
  maxMismatch = get_param("maxMismatch", 0),
  trimOverhang = get_param("trimOverhang", FALSE),
  justConcatenate = get_param("justConcatenate", FALSE)
)
if (nrow(mergers) == 0) {
  stop("DADA2 paired-end merge produced zero ASVs")
}
seqtab <- makeSequenceTable(list(sample = mergers))
seqtab <- remove_chimeras(seqtab)
summary_rows <- data.frame(step = "filtered_existing", input = NA_integer_, filtered = reads_f)
write_outputs(seqtab, summary_rows)
