suppressPackageStartupMessages({
  library(dada2)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  stop("Usage: Rscript dada2_pipeline.R manifest.json")
}

manifest <- fromJSON(args[[1]], simplifyVector = FALSE)
outdir <- manifest$output_dir
dir.create(outdir, showWarnings = FALSE, recursive = TRUE)
params <- manifest$params

filtered_dir <- file.path(outdir, "filtered")
dir.create(filtered_dir, showWarnings = FALSE, recursive = TRUE)

get_param <- function(name, default) {
  value <- params[[name]]
  if (is.null(value)) default else value
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

if (manifest$read_mode == "single") {
  filt <- file.path(filtered_dir, "R1_filtered.fastq.gz")
  trunc_len <- get_param("truncLen", list(0))[[1]]
  trim_left <- get_param("trimLeft", list(0))[[1]]
  out <- filterAndTrim(
    manifest$fastq_r1, filt,
    truncLen = trunc_len,
    trimLeft = trim_left,
    maxN = get_param("maxN", 0),
    maxEE = get_param("maxEE", list(2))[[1]],
    truncQ = get_param("truncQ", 2),
    compress = TRUE,
    multithread = TRUE
  )
  err <- learnErrors(filt, multithread = TRUE, nbases = get_param("nbases", 1e8))
  derep <- derepFastq(filt)
  dada_result <- dada(
    derep,
    err = err,
    multithread = TRUE,
    pool = get_param("pool", FALSE),
    OMEGA_A = get_param("omegaA", 1e-40),
    BAND_SIZE = get_param("bandSize", 16)
  )
  seqtab <- makeSequenceTable(list(sample = dada_result))
  seqtab <- remove_chimeras(seqtab)
  summary_rows <- data.frame(step = rownames(out), input = out[, 1], filtered = out[, 2])
  write_outputs(seqtab, summary_rows)
} else if (manifest$read_mode == "paired") {
  filt_f <- file.path(filtered_dir, "R1_filtered.fastq.gz")
  filt_r <- file.path(filtered_dir, "R2_filtered.fastq.gz")
  trunc_len <- get_param("truncLen", list(240, 200))
  trim_left <- get_param("trimLeft", list(0, 0))
  max_ee <- get_param("maxEE", list(2, 2))
  out <- filterAndTrim(
    manifest$fastq_r1, filt_f,
    manifest$fastq_r2, filt_r,
    truncLen = unlist(trunc_len),
    trimLeft = unlist(trim_left),
    maxN = get_param("maxN", 0),
    maxEE = unlist(max_ee),
    truncQ = get_param("truncQ", 2),
    compress = TRUE,
    multithread = TRUE
  )
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
  summary_rows <- data.frame(step = rownames(out), input = out[, 1], filtered = out[, 2])
  write_outputs(seqtab, summary_rows)
} else {
  stop(paste("Unsupported read mode:", manifest$read_mode))
}
