import gzip
import pytest


VALID_FASTA = """\
>seq1 first sequence
ATGCATGCATGC
>seq2 second sequence
GCGCGCGCGCGC
>seq3 third sequence
ATATATATATAT
"""

INVALID_FASTA_BAD_CHARS = """\
>seq1
ATGCXXXXATGC
"""

INVALID_FASTA_DOUBLE_HEADER = """\
>seq1
>seq2
ATGCATGC
"""

EMPTY_FASTA = ""


@pytest.fixture
def valid_fasta(tmp_path):
    p = tmp_path / "test.fasta"
    p.write_text(VALID_FASTA)
    return p


@pytest.fixture
def valid_fasta_gz(tmp_path):
    p = tmp_path / "test.fasta.gz"
    with gzip.open(p, "wt") as f:
        f.write(VALID_FASTA)
    return p


@pytest.fixture
def invalid_fasta_bad_chars(tmp_path):
    p = tmp_path / "bad_chars.fasta"
    p.write_text(INVALID_FASTA_BAD_CHARS)
    return p


@pytest.fixture
def invalid_fasta_double_header(tmp_path):
    p = tmp_path / "double_header.fasta"
    p.write_text(INVALID_FASTA_DOUBLE_HEADER)
    return p


@pytest.fixture
def empty_fasta(tmp_path):
    p = tmp_path / "empty.fasta"
    p.write_text(EMPTY_FASTA)
    return p
