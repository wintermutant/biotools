'''
Module for all things fasta
'''
import gzip
import logging
from dataclasses import dataclass
import pathlib
import sys
from typing import Literal

import typer

from biotools.base_classes import BaseInputProcessor, Result, command

LOGGER = logging.getLogger('biotools.fasta')


@dataclass
class FastaRecord:
    header: str
    sequence: str


class Fasta(BaseInputProcessor):
    '''Class that takes in 1 or more Fasta entries through either:
    a file, stream, or memory (dictionary or Python variable)
    # TODO: allow a dictionary or stream instead of just a file
    The content of the fasta file will be stored in memory in this class through the
    fasta_key variable. This fasta_key is the interface from the Fasta class holding
    the data to the biomodels.fasta model, which then interfaces with the database
    Fasta()::fasta_key --> biomodels.fasta::SQLModel --> Postgres / SQLite3 db

    When we iterate through all the fasta entries/rows in this class, we want to add these
    to a FastaEntry SQLModel, which in turn connects this model to all the other models
    (Sequence, FileObject, etc.) and takes care of the relational aspects.

    Later, when we query the db for stats, biomodels is in charge of this. Such as,
    biomodels.fasta(query). IMPORTANT: biomodels ONLY QUERIES AND RETRIEVES THE ROW-LEVEL
    data. IT DOES NOT create summaries and stats like retrieving all entries between 8-10
    bp long and getting the mean GC content. That functionality should either be in biotools
    and do the functionality on top of retrieval, or if it's common, PERHAPS in biomodels as
    a standard retrieve-and-summarize function. The advantage here is directly querying and creating
    the summary in 1 step and utilizing the db's functionality, versus 1) retrieving and then 2)
    creating the summary from all the data that would be in memory.
    '''
    known_extensions = ['.fna', '.fasta', '.fa']
    preferred_extension = '.fasta.gz'

    def __init__(
            self, file=None, detect_mode="medium",
            run_mode: 'Literal["module", "cli"]' = 'module'
            ) -> None:
        self.file, self.detect_mode, self.run_mode = file, detect_mode, run_mode
        if self.run_mode == 'cli':
            super().__init__(detect_mode=detect_mode, run_mode=run_mode, filetype='fasta')
        elif self.run_mode == 'module' and self.file:
            super().__init__(run_mode=run_mode)
            LOGGER.debug('Not running in cli mode')
            self.file_path = pathlib.Path(self.file)
            self.file_name = self.file_path.name
        else:
            LOGGER.warning('No file detected, triggering sys.exit within module...')
            sys.exit('Error: When running in module mode, a file must be provided')

        # ------------------------------- Custom stuff ------------------------------- #
        self.data_key: dict[int, FastaRecord] = {}
        self.written_output = []

        # --------------------------- Filename and Content Validation stuff ---------- #
        self.basename = self._compute_basename()
        self.preferred_file_path = self.std_filename()
        self.valid_extension = self.is_known_extension()
        self.valid = self.is_valid()

    def validate(self, open_file) -> bool:
        '''
        Validate the Fasta file and hydrate self.fasta_key, a dictionary of the fasta file
        in the form:
        {entry_index: (header, sequence)}
        '''
        if self.detect_mode == 'soft':
            LOGGER.debug('Detecting in soft mode, only checking extension')
            return self.valid_extension
        LOGGER.debug('Detecting comprehensively')

        valid_chars = set('ATGCNatgcn')
        prev_header = False
        current_header = ''
        current_seq = ''
        cnt = 0
        try:
            line = next(open_file)
        except StopIteration:
            return False
        while line:
            line = line.strip()
            if not line:
                line = next(open_file)
                continue
            if line.startswith('>'):
                cnt += 1
                current_header = line.strip()
                current_seq = ''
                if prev_header:
                    LOGGER.error('2 headers in a row')
                    self.data_key = {}
                    return False
                prev_header = True
                line = next(open_file)
            else:
                while line and not line.startswith('>'):
                    if not set(line).issubset(valid_chars):
                        LOGGER.error('Line has invalid character: %s', line)
                        return False
                    else:
                        current_seq += line.strip()
                        try:
                            line = next(open_file).strip()
                        except StopIteration:
                            line = None
                #TODO: maybe add the model from biomodels.fasta?
                self.data_key[cnt] = FastaRecord(
                    header=self.clean_header(current_header),
                    sequence=current_seq.upper()
                )
                # self.fasta_key[cnt] = (self.clean_header(current_header), current_seq.upper())

                prev_header = False

        return True
    

    def _to_db_model(self, data_key, db_model):  # -> list[FastaDbModel]
        """Convert data_key entries to a list of db_model instances."""
        #TODO this may be better abstracted and added to BaseInputProcessor. For now, it doesnt need to be abstracted
        return [
            db_model(header=record.header, sequence=record.sequence, source_file=self.file_name)
            for record in data_key.values()
        ]

    @command
    def do_db(self, **kwargs):
        '''Write fasta records to the configured database
        TODO: Add a db entry for log information that goes along with the row entry
        TODO: Add a 'note' section for adding notes
        '''
        from biomodels.app import create_db_and_tables
        from biomodels.db_connectors import db_connection
        from biomodels.db_connectors.fasta import ingest_fasta_records

        if not db_connection():
            LOGGER.warning('No db_connection...')
            return Result(data=None, msg="DB connection failed — check BIOMODELS_DB_CONNECTION in .env")

        create_db_and_tables()
        LOGGER.info('Getting read to ingest...')
        reserved = {'file', 'type', 'report.form'}
        metadata = {str(k): self.conf[k] for k in self.conf.allKeys if str(k) not in reserved} or None
        summary = ingest_fasta_records(filename=self.file_name, data_key=self.data_key, file_metadata=metadata)
        return Result(data=summary, msg=f"Ingested {summary['entries']} entries from {self.file_name} ({summary['sequences_created']} new sequences, {summary['sequences_reused']} reused)")

    # ~~~ Rewriting ~~~ #
    @command
    def do_write_confident(self, **kwargs):
        '''
        Here, we always want the same extension and compression: .fasta.gz
        We also want to ensure only ATGCN and each sequence is on 1 line
        '''
        if not self.valid:
            self.failed(msg='File is not valid')
            return None

        output = self.conf.get('output', None)
        if not output:
            output = self.preferred_file_path
        output = pathlib.Path(output)
        if output.suffix in ['.gz', '.gzip']:
            with gzip.open(str(self.preferred_file_path), 'wt') as open_file:
                for _, record in self.data_key.items():
                    open_file.write(f'>{record.header}\n{record.sequence}\n')
        else:
            with open(str(output), 'w', encoding='utf-8') as open_file:
                for _, record in self.data_key.items():
                    open_file.write(f'>{record.header}\n{record.sequence}\n')

        return Result(data=str(output), msg=f"Wrote output file to {output}")

    @command
    def do_write_table(self, **kwargs):
        '''Tabular output'''
        if not self.valid:
            self.failed(msg='File is not valid')
            return None

        output = self.conf.get('output', None)
        if not output:
            output = self.file_path.stem + '-VALIDATED.txt.gz'
        output = pathlib.Path(output)

        if output.suffix in ['.gz', '.gzip']:
            with gzip.open(str(output), 'wt') as open_file:
                for _, record in self.data_key.items():
                    open_file.write(f'{record.header},{record.sequence}\n')
        else:
            with open(str(output), 'w') as open_file:
                for _, record in self.data_key.items():
                    open_file.write(f'{record.header},{record.sequence}\n')
        return Result(data=str(output), msg=f"Wrote output file to {output}")

    @command
    def do_write_binid(self, output: str | None = None, **kwargs):
        # TODO: Change the name of this
        '''Create a bin ID file from the fasta file in the form: header,filename\n'''
        output = self.conf.get('output', None)
        if not output:
            output = self.file_path.with_name(f'{self.basename}-BinID.txt.gz')
        output = pathlib.Path(output)

        if output.suffix in ['.gz', '.gzip']:
            with gzip.open(str(output), 'wt') as open_file:
                for _, record in self.data_key.items():
                    open_file.write(f'{record.header},{self.file_name}\n')
        else:
            with open(str(output), 'w') as open_file:
                for _, record in self.data_key.items():
                    open_file.write(f'{record.header},{self.file_name}\n')
        return Result(data=str(output), msg=f"Wrote the binID file to {output}")

    # ~~~ Common Properties ~~~ #
    @staticmethod
    def clean_header(header: str) -> str:
        '''Remove headers initial > and replace spaces with _
        Some programs don't like spaces in headers'''
        if header.startswith('>'):
            clean_header = header[1:]
        else:
            clean_header = header
        clean_header = clean_header.replace(' ', '_')
        return clean_header

    # PROPERTIES
    @command
    def do_all_headers(self, **kwargs):
        '''Return all headers to standard out'''
        data = [v.header for v in self.data_key.values()]
        return Result(data=data, msg=f"All headers:\n{data}")

    @command
    def do_all_seqs(self, **kwargs):
        '''Return all sequences to standard out'''
        data = [v.sequence for v in self.data_key.values()]
        return Result(data=data, msg=f"All sequences:\n{data}")

    @command
    def do_gc_content(self, precision: int = 2, **kwargs):
        '''Return the GC content of each sequence in the fasta file'''
        precision = 2
        gc_content = {}
        for cnt, record in self.data_key.items():
            gc_count = record.sequence.count('G') + record.sequence.count('C')
            percent = round(gc_count / len(record.sequence), precision)
            gc_content[cnt] = (record.header, percent)
        return Result(data=gc_content, msg=f"GC Content per entry:\n{gc_content}")

    @command
    def do_gc_content_total(self, precision: int = 2, **kwargs):
        '''Return the average GC content across all sequences in the fasta file'''
        values = []
        for record in self.data_key.values():
            gc_count = record.sequence.count('G') + record.sequence.count('C')
            gc_content = (gc_count / len(record.sequence)) * 100 if record.sequence else 0
            values.append(round(gc_content, precision))
        data = round(sum(values) / len(values), precision) if values else 0
        return Result(data=data, msg=f"Total GC Content: {data}")

    @command
    def do_total_seqs(self, **kwargs) -> int | None:
        '''Return the total number of sequences (entries) in the fasta file.'''
        data = len(self.data_key)
        return Result(data=data, msg=f"Total sequences: {data}")

    @command
    def do_total_seq_length(self, **kwargs):
        '''Return the total length of all sequences in the fasta file'''
        data = sum(len(v.sequence) for v in self.data_key.values())
        return Result(data=data, msg=f"Total sequence length: {data}")

    @command
    def do_filter_seqlength(
        self,
        min_length: int = typer.Option(2000, "--min-length", "-l", help="Minimum sequence length to keep"),
        output_file: str = typer.Option(None, "--output", "-o", help="Output file path"),
        **kwargs
    ) -> Result:
        '''Filter the sequences by length, keeping only sequences above the minimum length'''
        seqlength = self.conf.get('seqlen', 2000)
        output = self.conf.get('output', None)
        if not output:
            output = self.file_path.with_name(f'{self.basename}-FILTERED-{seqlength}bp.txt')

        with open(output, 'wt', encoding="utf-8") as open_file:
            for record in self.data_key.values():
                if len(record.sequence) > seqlength:
                    open_file.write(f'>{record.header}\n{record.sequence}\n')
        data = {'seqlength': seqlength, 'output': str(output), 'action': 'filter_seqlength'}
        return Result(data=data, msg=f'Processed with seqlength of {seqlength} and wrote to output: {output}')

    @command
    def do_n_largest_seqs(
        self,
        n: int = typer.Option(10, "--count", "-n", help="Number of largest sequences to return"),
        output_file: str = typer.Option(None, "--output", "-o", help="Output file path"),
        **kwargs
    ):
        '''Return the n largest sequences in the fasta file'''
        # FIXME: What's confusing is we have the argument "n" like the user adds the -n int flag, but we don't
        # actually grab n as usual. This is due to caragols setting it in self.conf[n] = int
        n = int(self.conf.get('n', 10))
        output = self.conf.get('output', None)
        if not output:
            output = self.file_path.with_name(f'{self.basename}-LARGEST-{n}.txt')

        sorted_values = self.sorted_fasta
        with open(output, 'wt', encoding="utf-8") as open_file:
            for count, (_, record) in enumerate(sorted_values.items()):
                if count >= n:
                    break
                open_file.write(f'>{record.header}\n{record.sequence}\n')
        data = {'n': n, 'output': str(output)}
        return Result(data=data, msg=f'Wrote {n} largest sequences to {output}')

    @command
    def do_seq_length(self, **kwargs):
        '''Return the length of a specific sequence'''
        data = {(k, v.header): len(v.sequence) for k, v in self.data_key.items()}
        return Result(data=data, msg=f"Sequence lengths: {data}")

    @command
    def do_search_subsequence(
        self,
        subsequence: str = typer.Argument(..., help="DNA/RNA subsequence to search for"),
        **kwargs
    ):
        '''Search for a subsequence in all sequences of the fasta file'''
        subsequence = self.conf.get('subsequence', None)
        if not subsequence:
            self.failed(msg='No subsequence provided. Please use subsequence: <subsequence>')
            return None
        results = {k: v for k, v in self.data_key.items() if subsequence in v.sequence}
        return Result(data=results, msg=f"The following entries contained the subsequence:\n{results}")

    @command
    def do_basic_stats(self, **kwargs):
        '''Return basic statistics of the fasta file'''
        total_seqs = len(self.data_key)
        total_length = sum(len(v.sequence) for v in self.data_key.values())
        values = [
            (sum(r.sequence.count(c) for c in 'GC') / len(r.sequence)) * 100
            for r in self.data_key.values() if r.sequence
        ]
        avg_gc = round(sum(values) / len(values), 2) if values else 0
        data = {
            'Total Sequences': total_seqs,
            'Total Sequence Length': total_length,
            'Total GC Content': avg_gc,
        }
        return Result(data=data, msg=f"Basic statistics:\n{data}")

    @property
    def sorted_fasta(self):
        ascending = self.conf.get('ascending', False)
        return dict(sorted(
            self.data_key.items(),
            key=lambda item: item[1].header.lower(),
            reverse=not ascending
        ))
