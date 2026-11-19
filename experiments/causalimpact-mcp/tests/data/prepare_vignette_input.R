source(file.path(getwd(), "renv", "activate.R"))
library(jsonlite)
set.seed(1)
x1 <- 100 + arima.sim(model = list(ar = 0.999), n = 100)
y <- 1.2 * x1 + rnorm(100)
y[71:100] <- y[71:100] + 10
data <- cbind(y, x1)
fixture <- list(data = unname(lapply(seq_len(nrow(data)), function(i) as.list(unname(data[i, ])))),
                pre_period = as.list(c(1, 70)), post_period = as.list(c(71, 100)),
                alpha = 0.05, model_args = list(), seed = NULL,
                column_names = as.list(c("response", "control")))
jsonlite::write_json(fixture, file.path("tests", "data", "vignette-input.json"),
                     auto_unbox = TRUE, pretty = TRUE, null = "null")
