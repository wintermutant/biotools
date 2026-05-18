# biotools

CLI and Python library for processing common bioinformatics file formats.

Part of a broader ecosystem of decoupled libraries:
- **caragols** — CLI framework, config management, reporting
- **biotools** — bioinformatics file processing (FASTA, VCF, etc.) (this package)
- **biomodels** — ORM models and DB ingestion
- **bioserver** — API service built on biotools + biomodels
- **biocompute** — SLURM/HPC connectivity

---

## Setup

```bash
uv pip install -e .
```

---

## CLI usage

Commands use `key: value` syntax rather than flags:

```bash
biotools type: fasta file: myfile.fasta <command>
```

### FASTA commands

```
db                  ingest records into the database
valid               check if the file parses correctly
gc content          per-entry GC content
gc content total    GC content across the entire file
total seqs          count of entries
total seq length    sum of all sequence lengths
seq length          length per entry
all headers         print all headers
all seqs            print all sequences
basic stats         summary of the above
filter seqlength    filter entries by min/max length
n largest seqs      return the N longest sequences
search subsequence  search for a subsequence
write confident     rewrite as validated .fasta.gz
write table         tabular output
write binid         write with bin identifiers
```

### Metadata on DB ingestion

Any extra `key: value` pairs passed at the CLI are stored as JSON metadata on the file record:

```bash
biotools type: fasta file: myfile.fasta db source: lab1 date: 2026-05-16
```

---

## Module usage

```python
from biotools.fasta import Fasta

fasta = Fasta(file="myfile.fasta")

print(fasta.data_key)      # dict[int, FastaRecord]
print(fasta.valid)         # True/False
```

Each entry in `data_key` is a `FastaRecord` dataclass with `header` and `sequence`.

---

## Design principles

- **biotools owns parsing only** — produces structured records, no DB logic
- **commands are plain methods** — usable from the CLI or directly in Python
- **biomodels is optional** — the `db` command pulls it in, but nothing else depends on it
