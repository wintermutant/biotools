import pathlib
import pytest
from biotools.fasta import Fasta


def make_fasta(path):
    return Fasta(file=str(path))


class TestCleanHeader:
    def test_strips_leading_gt(self):
        assert Fasta.clean_header('>seq1') == 'seq1'

    def test_replaces_spaces_with_underscores(self):
        assert Fasta.clean_header('>seq 1 description') == 'seq_1_description'

    def test_no_gt_passthrough(self):
        assert Fasta.clean_header('seq1') == 'seq1'

    def test_empty_string(self):
        assert Fasta.clean_header('') == ''


class TestFastaValidation:
    def test_valid_fasta_is_valid(self, valid_fasta):
        f = make_fasta(valid_fasta)
        assert f.valid is True

    def test_valid_fasta_gz_is_valid(self, valid_fasta_gz):
        f = make_fasta(valid_fasta_gz)
        assert f.valid is True

    def test_invalid_bad_chars(self, invalid_fasta_bad_chars):
        f = make_fasta(invalid_fasta_bad_chars)
        assert f.valid is False

    def test_invalid_double_header(self, invalid_fasta_double_header):
        f = make_fasta(invalid_fasta_double_header)
        assert f.valid is False

    def test_empty_file_is_invalid(self, empty_fasta):
        f = make_fasta(empty_fasta)
        assert f.valid is False

    def test_nonexistent_file_is_invalid(self, tmp_path):
        f = make_fasta(tmp_path / "nonexistent.fasta")
        assert f.valid is False


class TestFastaKey:
    def test_entry_count(self, valid_fasta):
        f = make_fasta(valid_fasta)
        assert len(f.fasta_key) == 3

    def test_header_stored_correctly(self, valid_fasta):
        f = make_fasta(valid_fasta)
        headers = [v[0] for v in f.fasta_key.values()]
        assert 'seq1_first_sequence' in headers

    def test_sequence_stored_uppercase(self, valid_fasta):
        f = make_fasta(valid_fasta)
        for _, (header, seq) in f.fasta_key.items():
            assert seq == seq.upper()

    def test_fasta_key_empty_on_invalid(self, invalid_fasta_bad_chars):
        f = make_fasta(invalid_fasta_bad_chars)
        assert f.fasta_key == {}


class TestFastaMethods:
    def test_total_seqs(self, valid_fasta):
        f = make_fasta(valid_fasta)
        assert f.do_total_seqs() == 3

    def test_total_seq_length(self, valid_fasta):
        f = make_fasta(valid_fasta)
        assert f.do_total_seq_length() == 36

    def test_gc_content_total(self, valid_fasta):
        # seq1: ATGCATGCATGC → 50%, seq2: GCGCGCGCGCGC → 100%, seq3: ATATATATATAT → 0% → avg 50.0
        f = make_fasta(valid_fasta)
        assert f.do_gc_content_total() == 50.0

    def test_gc_content_per_entry(self, valid_fasta):
        f = make_fasta(valid_fasta)
        result = f.do_gc_content()
        assert len(result) == 3
        gc_percents = [v[1] for v in result.values()]
        assert 0.5 in gc_percents   # seq1: ATGCATGCATGC
        assert 1.0 in gc_percents   # seq2: GCGCGCGCGCGC
        assert 0.0 in gc_percents   # seq3: ATATATATATAT

    def test_gc_content_all_gc(self, tmp_path):
        p = tmp_path / "allgc.fasta"
        p.write_text(">seq1\nGCGCGCGCGCGC\n")
        f = make_fasta(p)
        assert f.do_gc_content_total() == 100.0

    def test_gc_content_no_gc(self, tmp_path):
        p = tmp_path / "nogc.fasta"
        p.write_text(">seq1\nATATATATATAT\n")
        f = make_fasta(p)
        assert f.do_gc_content_total() == 0.0

    def test_all_headers(self, valid_fasta):
        f = make_fasta(valid_fasta)
        headers = f.do_all_headers()
        assert len(headers) == 3
        assert 'seq1_first_sequence' in headers

    def test_all_seqs(self, valid_fasta):
        f = make_fasta(valid_fasta)
        seqs = f.do_all_seqs()
        assert len(seqs) == 3
        assert 'ATGCATGCATGC' in seqs

    def test_basic_stats(self, valid_fasta):
        f = make_fasta(valid_fasta)
        stats = f.do_basic_stats()
        assert stats['Total Sequences'] == 3
        assert stats['Total Sequence Length'] == 36
        assert stats['Total GC Content'] == 50.0


class TestWriteBinid:
    def test_explicit_output_plain(self, valid_fasta, tmp_path):
        f = make_fasta(valid_fasta)
        output = tmp_path / 'binid.txt'
        f.do_write_binid(output=str(output))
        assert output.exists()
        lines = output.read_text().splitlines()
        assert len(lines) == 3
        assert all(',' in line for line in lines)
        assert all(f.file_name in line for line in lines)

    def test_explicit_output_gz(self, valid_fasta, tmp_path):
        import gzip
        f = make_fasta(valid_fasta)
        output = tmp_path / 'binid.txt.gz'
        f.do_write_binid(output=str(output))
        assert output.exists()
        with gzip.open(output, 'rt') as fh:
            lines = fh.read().splitlines()
        assert len(lines) == 3

    def test_default_output_path(self, valid_fasta):
        f = make_fasta(valid_fasta)
        result_path = f.do_write_binid()
        assert pathlib.Path(result_path).exists()

    def test_header_and_filename_in_output(self, valid_fasta, tmp_path):
        f = make_fasta(valid_fasta)
        output = tmp_path / 'binid.txt'
        f.do_write_binid(output=str(output))
        lines = output.read_text().splitlines()
        headers = [line.split(',')[0] for line in lines]
        assert 'seq1_first_sequence' in headers
