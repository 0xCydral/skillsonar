---
name: csv-data-cleaning
description: Clean messy CSV and spreadsheet exports with pandas. Fix encodings, trim whitespace, parse dates, drop duplicates and report rows that fail validation.
---

# CSV data cleaning

## Load safely
Read everything as strings first, set `encoding` explicitly (try utf-8, then cp1252) and
keep a copy of the raw file untouched.

## Normalize
Trim whitespace, unify casing, parse dates with an explicit format and convert numeric
columns with `errors="coerce"`, counting what failed.

## Duplicates and report
Deduplicate on a business key, not on the whole row. Write rejected rows to a separate file
with the reason.
