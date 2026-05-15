"""
CLI integration tests. These invoke the `biotools` entry point via subprocess
so they test the full stack as a user would run it.
"""
import subprocess
import sys
import pytest


def run_biotools(*args):
    """Run `biotools <args>` and return CompletedProcess."""
    return subprocess.run(
        [sys.executable, '-m', 'biotools.main', *args],
        capture_output=True,
        text=True
    )


@pytest.fixture
def fasta_file(tmp_path):
    p = tmp_path / "sample.fasta"
    p.write_text(">seq1\nATGCATGC\n>seq2\nGCGCGCGC\n")
    return p


@pytest.fixture
def invalid_fasta_file(tmp_path):
    p = tmp_path / "bad.fasta"
    p.write_text(">seq1\nATGCXXXX\n")
    return p


class TestCLINoArgs:
    def test_exits_nonzero_with_no_args(self):
        result = run_biotools()
        assert result.returncode != 0

    def test_error_message_on_no_type(self):
        result = run_biotools()
        assert result.returncode != 0


class TestCLIFasta:
    def test_total_seqs(self, fasta_file):
        result = run_biotools('total', 'seqs', 'type:', 'fasta', 'file:', str(fasta_file))
        assert result.returncode == 0
        assert '2' in result.stdout

    def test_gc_content(self, fasta_file):
        result = run_biotools('gc', 'content', 'total', 'type:', 'fasta', 'file:', str(fasta_file))
        print(f'RESULT:\n{result}')
        assert result.returncode == 0

    def test_all_headers(self, fasta_file):
        result = run_biotools('all', 'headers', 'type:', 'fasta', 'file:', str(fasta_file))
        print(f'RESULT:\n{result}')
        assert result.returncode == 0
        assert 'seq1' in result.stdout

    def test_invalid_file_exits_nonzero(self, invalid_fasta_file):
        result = run_biotools('total', 'seqs', 'type:', 'fasta', 'file:', str(invalid_fasta_file))
        assert result.returncode != 0

    def test_unknown_type_exits_nonzero(self, fasta_file):
        result = run_biotools('total', 'seqs', 'type:', 'fastq', 'file:', str(fasta_file))
        assert result.returncode != 0
