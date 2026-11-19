source(file.path(getwd(), "renv", "activate.R"))
library(CausalImpact)

set.seed(1)
x1 <- 100 + arima.sim(model = list(ar = 0.999), n = 100)
y <- 1.2 * x1 + rnorm(100)
y[71:100] <- y[71:100] + 10
data <- cbind(y, x1)
pre.period <- c(1, 70)
post.period <- c(71, 100)

impact <- CausalImpact(data, pre.period, post.period)

out <- file.path("tests", "results")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
capture.output(summary(impact), file = file.path(out, "vignette-summary.txt"))
write.csv(as.data.frame(impact$summary),
          file.path(out, "vignette-summary-numeric.csv"), row.names = FALSE)
write.csv(as.data.frame(impact$series),
          file.path(out, "vignette-series.csv"), row.names = TRUE)
writeLines(capture.output(sessionInfo()), file.path(out, "session-info.txt"))
grDevices::pdf(file.path(out, "vignette-impact.pdf"), width = 8, height = 6)
plot(impact)
grDevices::dev.off()
