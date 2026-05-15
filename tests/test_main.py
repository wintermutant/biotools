import pytest
from biotools.fasta import Fasta
from biotools.main import find_file_type, match_type_to_class


class TestFindFileType:
    def test_finds_fasta_type(self):
        assert find_file_type(['biotools', 'type:', 'fasta']) == 'fasta'

    def test_lowercases_type(self):
        assert find_file_type(['biotools', 'type:', 'FASTA']) == 'fasta'

    def test_returns_none_when_missing(self):
        assert find_file_type(['biotools', 'file:', 'something.fasta']) is None

    def test_returns_none_on_empty(self):
        assert find_file_type([]) is None

    def test_finds_type_anywhere_in_args(self):
        assert find_file_type(['file:', 'foo.fasta', 'type:', 'fasta']) == 'fasta'


class TestMatchTypeToClass:
    def test_matches_fasta(self):
        assert match_type_to_class('fasta') is Fasta

    def test_unknown_type_returns_none(self):
        assert match_type_to_class('fastq') is None

    def test_none_input_returns_none(self):
        assert match_type_to_class(None) is None

    def test_empty_string_returns_none(self):
        assert match_type_to_class('') is None
