'''
Main functionality for the biotools package. This is where the CLI comes through as an entrypoint.
'''
import logging
import sys

from biotools.fasta import Fasta

from caragols.logger import config_logging_for_app

LOGGER = logging.getLogger('biotools')

CLASS_MAPPER = {
    'fasta': Fasta
}


def find_file_type(args: list) -> None | str:
    '''
    This function takes in a list of arguments and determines what type of file
    it is. It then returns the class that can handle that file.
    '''
    type_ = None
    for cnt, arg in enumerate(args):
        if arg.startswith('type:'):
            type_ = args[cnt + 1]
            type_ = type_.lower()
            break
    return type_


def match_type_to_class(type_: str | None) -> type[Fasta] | None:
    if not type_:
        return None
    return CLASS_MAPPER.get(type_, None)


def cli():
    config_logging_for_app(app_name='biotools')
    type_ = find_file_type(sys.argv)
    MatchedClass = match_type_to_class(type_)
    print(f'Type found!')
    if type_ and MatchedClass:
        print(f'Matched')
        LOGGER.info('Matched!')
        data = MatchedClass(run_mode='cli')
        print(f'Inited class')
        if not data.valid:
            print(f'Data not valid...')
            LOGGER.debug('Data provided failed validation test')
            sys.exit('Invalid return of data.valid')
        data.run()

    else:
        print('Not type match!')
        if any(arg.lower() in sys.argv for arg in ('help')):
            LOGGER.info('🆘 Help requested')
            LOGGER.info('The following file types are recognized and can be specified via the command line\n\033[92mbiotools type: <file_type>\033[0m')
            help_string = 'Available file types:\n'
            for type_identifier in CLASS_MAPPER:
                help_string += f'{type_identifier[0]}\n'
            LOGGER.info(help_string)
            sys.exit('Exited without a report do to main help message')
        LOGGER.error('No file type provided. Please specify via the command line\nbiotools type: <file_type>\nExiting...')
        sys.exit('Exited without a report due to no file type')


if __name__ == "__main__":
    cli()