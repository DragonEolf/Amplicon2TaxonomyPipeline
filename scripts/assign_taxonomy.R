suppressPackageStartupMessages({
  library(dada2)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1) {
  stop("Usage: Rscript assign_taxonomy.R manifest.json")
}

manifest <- fromJSON(args[[1]], simplifyVector = FALSE)
ranks <- c("kingdom", "phylum", "class", "order", "family", "genus", "species")

read_fasta <- function(path) {
  lines <- readLines(path, warn = FALSE)
  ids <- character()
  seqs <- character()
  current_id <- NULL
  current_seq <- character()

  flush_record <- function() {
    if (!is.null(current_id)) {
      ids <<- c(ids, current_id)
      seqs <<- c(seqs, paste0(current_seq, collapse = ""))
    }
  }

  for (line in lines) {
    if (startsWith(line, ">")) {
      flush_record()
      current_id <- sub("^>", "", line)
      current_id <- strsplit(current_id, "\\s+")[[1]][1]
      current_seq <- character()
    } else if (nzchar(line)) {
      current_seq <- c(current_seq, toupper(trimws(line)))
    }
  }
  flush_record()
  names(seqs) <- ids
  seqs
}

seqs <- read_fasta(manifest$asv_fasta)
tax_result <- assignTaxonomy(
  seqs,
  manifest$training_fasta,
  minBoot = manifest$min_boot,
  tryRC = manifest$try_rc,
  outputBootstraps = TRUE,
  multithread = TRUE
)
tax <- tax_result$tax
boot <- tax_result$boot

out <- data.frame(
  asv_id = names(seqs),
  database = manifest$database,
  match_type = "assign_taxonomy",
  identity = "",
  kingdom = "",
  phylum = "",
  class = "",
  order = "",
  family = "",
  genus = "",
  species = "",
  stringsAsFactors = FALSE
)

if (!is.null(dim(tax)) && nrow(tax) > 0) {
  colnames(tax) <- tolower(colnames(tax))
  colnames(boot) <- tolower(colnames(boot))
  for (rank in ranks) {
    if (rank %in% colnames(tax)) {
      values <- tax[, rank]
      values[is.na(values)] <- ""
      boot_values <- boot[, rank]
      values <- ifelse(
        values == "",
        "",
        paste0(values, " (", ifelse(is.na(boot_values), "", boot_values), ")")
      )
      out[[rank]] <- values
    }
  }
}

write.csv(out, manifest$output_csv, row.names = FALSE, quote = FALSE)
