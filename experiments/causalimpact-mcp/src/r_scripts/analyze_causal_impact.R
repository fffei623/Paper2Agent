args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("usage: analyze_causal_impact.R <input.json> <output-directory>")

source(file.path(getwd(), "renv", "activate.R"))
suppressPackageStartupMessages({
  library(CausalImpact)
  library(jsonlite)
  library(zoo)
})
input <- jsonlite::fromJSON(args[[1]], simplifyVector = FALSE)
out_dir <- args[[2]]
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

rows <- input$data
if (!is.list(rows) || length(rows) < 4L || !all(vapply(rows, is.list, logical(1))))
  stop("data must be a rectangular array with at least four rows")
widths <- vapply(rows, length, integer(1))
if (length(unique(widths)) != 1L || widths[[1]] < 1L)
  stop("data must have at least one column and equal row lengths")
data <- do.call(rbind, lapply(rows, function(row) {
  vapply(row, function(value) if (is.null(value)) NA_real_ else as.numeric(value), numeric(1))
}))
storage.mode(data) <- "double"
if (ncol(data) > 1L && anyNA(data[, -1L, drop = FALSE]))
  stop("covariate columns (all columns after the response) cannot contain null/NA values")
if (!is.null(input$column_names)) {
  if (length(input$column_names) != ncol(data)) stop("column_names length must match data columns")
  colnames(data) <- unlist(input$column_names, use.names = FALSE)
}
period <- function(value, name) {
  if (!is.list(value) || length(value) != 2L) stop(paste0(name, " must contain two boundaries"))
  unlist(value, use.names = FALSE)
}
pre <- period(input$pre_period, "pre_period")
post <- period(input$post_period, "post_period")
alpha <- if (is.null(input$alpha)) 0.05 else as.numeric(input$alpha)
if (!is.null(input$seed)) set.seed(as.integer(input$seed))
model_args <- input$model_args
if (is.null(model_args)) model_args <- list()
if (!is.list(model_args)) stop("model_args must be a JSON object")

impact <- CausalImpact(data = data, pre.period = pre, post.period = post,
                       model.args = model_args, alpha = alpha)
series <- as.data.frame(impact$series)
series <- cbind(time = as.numeric(zoo::index(impact$series)), series)
utils::write.csv(series, file.path(out_dir, "impact-series.csv"), row.names = FALSE, na = "")
grDevices::pdf(file.path(out_dir, "impact-plot.pdf"), width = 8, height = 6)
plot(impact)
grDevices::dev.off()
result <- list(package_version = as.character(utils::packageVersion("CausalImpact")),
               pre_period = as.list(pre), post_period = as.list(post), alpha = alpha,
               summary = impact$summary, report = impact$report,
               series_csv = "impact-series.csv", plot_pdf = "impact-plot.pdf")
jsonlite::write_json(result, file.path(out_dir, "result.json"), auto_unbox = TRUE,
                     null = "null", na = "null", pretty = TRUE, dataframe = "rows")
