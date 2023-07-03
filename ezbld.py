'''Tool for file composition (building)'''

import sys
import os
import configparser
import argparse
import re
import logging
from importlib import import_module
from datetime import datetime
from enum import Enum

BUILD_SETTINGS = 'settings.ini'
DEFAULT_LOG_LEVEL = logging.INFO
LOG_TO_FILE = '{project}_{version}_{timestamp}_log.log'
LOG_FORMAT = '%(levelname)s (%(asctime)s): [%(filename)s::%(funcName)s] %(message)s'

# File processor related
processors = {}

class ProcessorInterface:
    '''Interface for processor class'''
    def check_for_instruction(self, line: str) -> bool:
        '''Checks given line for instruction syntax and
           returns True if instruction found, otherwise False.
           Processor must save supported instruction for futher use.
        '''

    def has_instructions(self) -> bool:
        '''Returns True if processor has any instruction found'''

    def process(self, content: list) -> list:
        '''Modify given content according to current instruction list'''


# Utility functions
def get_path_relative_to_app(rel_path: str) -> str:
    """Composes abs path relatively to application directory"""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, rel_path)

def get_path_relative_to_cwd(rel_path: str) -> str:
    """Composes abs path relatively to current working directory"""
    return os.path.join(os.getcwd(), rel_path)

def print_progress_bar(current, limit, size=40, label='Progress', bar_char='*', empty_char=' '):
    '''Prints progress bar'''
    percentage = int(current / limit * 100)
    width = int(current / limit * size)
    progress_bar = "[%s%s]" % (
        bar_char * width,
        empty_char * (size - width)
    )

    print('{label}: {progress_bar} {percentage:>2}%'.format(label=label, progress_bar=progress_bar, percentage=percentage))


# Build functions
class SourceFilesMarkup(Enum):
    '''Recognized types of entity at artifacts.ini->order section'''
    FILE = 1
    TEXT_INSERT = 2


def get_last_build_version(version_track_filename) -> int:
    ''' Reads saved version of the last build from given file.
    '''
    if not os.path.exists(version_track_filename):
        return 0

    version = 0
    with open(version_track_filename, 'r', encoding='utf-8') as bvf:
        line = bvf.readline()
        version = int(line) + 1

    return version

def save_build_version(version_track_filename, version: int) -> None:
    '''Saves build version of build to the given file.
    '''
    with open(version_track_filename, 'w', encoding='utf-8') as bvf:
        bvf.write(str(version))

def process_file(filename: str, processor_name: str = None) -> str:
    '''Reads source file and checks for processor instructions.
       If needed - content is passed to processor for modification,
       otherwise returns file content
       Each artifact may use only one processr (defined in build setting file).

       Parameters:
       str: filename -- filename of the source file.
       str: processor_name -- name of the processor to apply.

       Returns:
       str: string of processed content
    '''
    content = []
    processor = processors.get(processor_name)() if processor_name else None

    with open(filename, 'r', encoding='utf-8') as src_file:
        if not processor:
            logging.info('\tNo processor name defined or'
                  ' processor for %s not found. Copy as is.', processor_name)
            return src_file.read()

        # Look for processor instructions in first lines of the file.
        # If any non-empty line without instruction met
        # stop checking and consider that instuction block is over
        for line in src_file:
            if not line.strip():
                continue

            # If instruction line found - add to list
            # if line is not an instruction - stop futher search
            instruction_found = processor.check_for_instruction(line)
            if not instruction_found:
                content = [
                    line,
                    *list(src_file)
                ]
                break

    if not processor.has_instructions():
        logging.info('\tThere is no processor instruction found. Copy as is.')
        return ''.join(content)

    content = processor.process(content)
    return ''.join(content)

def scan_sources(source_dir: str, files: list): # -> (Tuple[str, SourceFilesMarkup], List[str])
    '''Reads through given list of files and generates
       path to file and type of entry (file, inline string or invalid)
    '''
    filelist = []
    invalid_files = []
    file_mask_pattern = re.compile(r'\*\.([a-zA-Z0-9]+)$')
    for filename in files:
        # Direct text inject
        if filename.startswith(">>"):
            filelist.append((filename, SourceFilesMarkup.TEXT_INSERT))
            continue

        filepath = os.path.join(source_dir, filename)

        # Masked files (*, *.md, etc.)
        search_result = file_mask_pattern.search(filepath)
        extension_filter = (tuple(search_result.group(1).split('|'))
                            if search_result else '')
        if filepath.endswith('*') or extension_filter:
            for entity in os.scandir(os.path.dirname(filepath)):
                if entity.is_dir() or not entity.name.lower().endswith(extension_filter):
                    continue

                filelist.append((entity.path, SourceFilesMarkup.FILE))
            continue

        # Normal files
        if not os.path.exists(filepath):
            invalid_files.append(filepath)
        else:
            filelist.append((filepath, SourceFilesMarkup.FILE))

    return tuple(filelist), invalid_files


def build_artifact(project_path: str,
                   settings: configparser.ConfigParser,
                   build_config: configparser.ConfigParser,
                   version: str) -> int:
    """
    Reads build configuration for particular artifacts and makes build.

    Parameters:
    str: project_path -- abs path to project core directory.
    configparser.ConfigParser: settings -- application config read from given 'settings.ini'
    configparser.ConfigParser: build_config -- single build config entry read from Settings.Files.config (e.g. 'artifacts.ini')
    str: version -- version of the current build

    Returns:
    int: Operation result (0 - success, -1 - error)
    """

    path_prefix = build_config.get('path', project_path)
    logging.info('Path prefix: %s', path_prefix)

    source_dir = (os.path.join(path_prefix, build_config.get('source_dir'))
                  if build_config.get('source_dir') else
                  settings['Paths']['defaultSourceDir'])

    if not os.path.exists(source_dir):
        logging.error('\n[ERROR] Source directory [%s] not exists!', source_dir)
        return -1

    is_release = settings['General'].getboolean('release')
    fail_on_missing_files = settings['General'].getboolean('failOnMissingFiles')

    logging.info('Source: %s', source_dir)

    target_dir = os.path.join(
                    path_prefix,
                    settings['Paths']['releaseTo' if is_release else 'buildTo']
                )
    if not os.path.exists(target_dir):
        logging.error('\n[ERROR] Target directory [%s] not exists!', target_dir)
        return -1

    # Adjust target directory according to artifact settings
    if build_config.get('target_dir'):
        target_dir = os.path.join(target_dir, build_config['target_dir'])
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            logging.warning('WARNING: Directories has been generated for path %s', target_dir)

    logging.info('Target: %s', target_dir)

    # Building
    artifact_filename = build_config.name
    artifact_full_filename = (artifact_filename
                              if is_release else
                              '%s-%s' % (artifact_filename,version))
    artifact_full_path = os.path.join(target_dir, artifact_full_filename)

    processor_name = build_config.get('processor')

    header_message = build_config.get('header_message')
    if header_message:
        header_message = '\n'.join(
            header_message.strip("\"'")
                          .format(version=version,
                                  timestamp=str(datetime.now()))
                          .split('\\n')
        )

    listed_files = [f.strip() for f in build_config['order'].splitlines() if f.strip()]
    source_files, invalid_source_files = scan_sources(source_dir, listed_files)
    if invalid_source_files:
        for invalid_file in invalid_source_files:
            logging.error('Missing source file: %s', invalid_file)

        if fail_on_missing_files:
            logging.critical('\nBuild failed. There are %s missing source file(s)',
                             len(invalid_source_files))
            return -1

    source_size = len(source_files)
    with open(artifact_full_path, 'w', encoding='utf-8') as artifact:
        if header_message:
            artifact.write(header_message)
            artifact.write('\n\n')

        for i, src_entry in enumerate(source_files):
            src_filename, src_type = src_entry

            if src_type == SourceFilesMarkup.TEXT_INSERT:
                artifact.write(src_filename[3:-1] + "\n")
                continue

            # Otherwise - file case
            print()
            logging.info('Entry %s/%s\n<%s>', i+1, source_size, src_filename)
            processed_content = process_file(src_filename, processor_name)

            artifact.write(processed_content)
            artifact.write('\n')

            print_progress_bar(i+1, source_size, label='\tArtifact build progress', bar_char='*')

    return 0

def load_processors(processors_settings):
    '''Loads line processors from settings file'''
    for processor_name, module_name in processors_settings.items():
        print('Loading processor [%s]' % processor_name)
        print('           module [%s]' % module_name)
        plugin = import_module(module_name)
        plugin_processor = plugin.get()
        processors[processor_name] = plugin_processor

        print('Loaded successfully!')
    print(processors)

def main(settings_file_path: str) -> int:
    '''Entry point.
       Validates configs and starts building process.'''

    # If Setting File is not passed as cmd argument - use default
    if not settings_file_path:
        settings_file_path = BUILD_SETTINGS

    # If path is absolute - just check if it exists
    # Otherwise - check for file relatively to cwd
    if not os.path.isabs(settings_file_path):
        settings_file_path = get_path_relative_to_cwd(settings_file_path)

    if not os.path.exists(settings_file_path):
        print('\n [ERROR] Failed to find settings file (%s)' % settings_file_path)
        return -1

    print('Using setting file %s' % settings_file_path)
    settings = configparser.ConfigParser()
    settings.read(settings_file_path, encoding='utf-8')

    # Project path is either defined in Settings File
    # or Settings File directory is used
    project_path = settings['Paths'].get('projectPath')
    if not project_path:
        project_path = os.path.join(os.path.dirname(settings_file_path))
    print('Project path: %s' % project_path)
    settings['Paths']['projectPath'] = project_path

    # Check for default source directory. If not set - set it to project path
    source_dir = settings['Paths'].get('defaultSourceDir')
    settings['Paths']['defaultSourceDir'] = (os.path.join(project_path, source_dir)
                                            if source_dir else
                                            project_path)

    # Load processors
    if settings.has_section('Processors'):
        load_processors(settings['Processors'])

    # Read build configuration
    build_cfg_file_path = os.path.join(project_path, settings['Files']['config'])
    if not os.path.exists(build_cfg_file_path):
        print('\n [ERROR] Failed to find build config file (%s)' % build_cfg_file_path)
        return -1

    cfg = configparser.ConfigParser()
    cfg.read(build_cfg_file_path, encoding='utf-8')

    # Validation and preparation
    if not cfg.sections():
        print('\n[ERROR] Failed to read %s file! There is no sections defined!'
              % build_cfg_file_path)
        return -1

    version_tracker_filename = os.path.join(project_path, settings['Files']['VersionTracker'])
    version = get_last_build_version(version_tracker_filename)
    full_version = '.'.join((
        str(settings["Version"]["major"]),
        str(settings["Version"]["minor"]),
        str(settings["Version"]["patch"]),
        str(version)
    ))
    print('Full version of the build: %s' % full_version)

    setup_logger(settings, full_version)

    build_config_sections = cfg.sections()
    for idx, artifact_config_name in enumerate(build_config_sections):
        build_config = cfg[artifact_config_name]
        logging.info('=' * 80)
        logging.info('%s of %s | Going to build artifact %s', idx+1, len(build_config_sections), artifact_config_name)
        logging.info('=' * 80)

        op_result = build_artifact(project_path, settings, build_config, full_version)
        if op_result < 0:
            logging.error('\n[ERROR] Failed to build artifact. Programm stopped')
            return -1

        print()
        print_progress_bar(idx+1, len(build_config_sections),
                           size=49, label='Overall build progress')

    logging.info('All done!')
    save_build_version(version_tracker_filename, version)

    return 0

def setup_logger(settings: configparser.ConfigParser, version: str):
    """Sets up logger configuration"""
    output_file = None
    log_entry_format=None
    level = DEFAULT_LOG_LEVEL

    if settings.has_section('Logging'):
        if settings['Logging'].get('logToFile') and settings['Logging'].getboolean('logToFile'):
            output_file = LOG_TO_FILE.format(
                project=os.path.basename(settings['Paths']['projectPath']),
                version=version,
                timestamp=datetime.now().strftime('%y%m%d_%H%M%S')
            )
            log_entry_format=LOG_FORMAT
            print('Logging to file is enabled. File: %s' % output_file)

        if settings['Logging'].get('level'):
            level = settings['Logging']['level'].upper()
            print('Log level detected in settings file: %s' % level)

    logging.basicConfig(
        filename=output_file,
        # encoding='utf-8',  # not working with Py3.4
        level=level,
        format=log_entry_format
    )
    if output_file:
        logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--settings_file', '-s',
        action='store',
        help='Absolute path to build settings INI file',
        default='',
        required=False
    )
    args = arg_parser.parse_args()

    BUILD_RESULT = main(args.settings_file.strip('\'"'))
    print('\n\nBuild finished with code %s' % BUILD_RESULT)
    sys.exit(BUILD_RESULT)
