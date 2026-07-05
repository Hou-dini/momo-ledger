terraform {
  backend "gcs" {
    bucket = "vibe-coding-intensive-course-terraform-state"
    prefix = "momo-ledger/dev"
  }
}
