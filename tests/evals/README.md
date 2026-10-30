# Evals live in `plugin/evals/`

`claude plugin eval` requires its case directory to be **below the plugin root**: the
default is `evals/` inside the plugin, and the `experimental.evals` manifest key can only
point at another directory under that same root
.

`tests/evals/` is a sibling of `plugin/`, so it cannot be an eval directory. The suite is
at [`../../plugin/evals/`](../../plugin/evals/), with its own README.

This file exists so that anyone who looks for the suite here is pointed at it.
