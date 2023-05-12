'''Tool for file composition (building)'''

import sys
import os
import configparser
import argparse
import logging
from importlib import import_module
from datetime import datetime
from enum import Enum

BUILD_SETTINGS = 'settings.ini'
DEFAULT_LOG_LEVEL = logging.INFO
LOG_TO_FILE = '{project}_{version}_{timestamp}_log.log'
LOG_FORMAT = '%(levelname)s (%(asctime)s): [%(filename)s::%(funcName)s] %(message)s'

class SourceFilesMarkup(Enum):
    INVALID = 0
    FILE = 1
    TEXT_INSERT = 2

processors = {}

class ProcessorInterface:
    '''Interface for processor class'''
    @staticmethod
    def get_definitions():
        '''Returns list of instruction definitions supported by processor'''

    @staticmethod
    def get_processor(instruction: str):
        '''Creates and returns processor function
            according to given instruction found in source file
        '''


def get_processor_definitions(processor_name):
    '''Compose list of processor instruction definitions to search in file content'''
    return processors[processor_name].get_definitions()

def get_processor(processor_name, params):
    '''Creates text processor using given params'''
    return processors[processor_name].get_processor(params)


# Build functions
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

def process_file(filename: str, processor_name) -> str:
    '''Reads source file and checks for processor directives.
       If needed - content passed to processor for modification,
       otherwise returns file content
       Input: Filename of the source file
       Returns: string of processed content
    '''
    content = []
    instructions = []
    with open(filename, 'r', encoding='utf-8') as src_file:
        if not processor_name or not processors.get(processor_name):
            logging.info('\tNo processor name defined or'
                  ' processor for %s not found. Copy as is.' % (processor_name))
            return src_file.read()

        # Look for processor instructions in first lines of the file.
        # If any non-empty line without instruction met
        # stop checking and consider that instuction block is over
        defines = get_processor_definitions(processor_name)
        for i, line in enumerate(src_file):
            if not line:
                continue

            # If instruction line found - add to list
            # if line is not an instruction - stop futher search
            if any((line.lower().startswith(define) for define in defines)):
                instructions.append(line)
            else:
                content = list(src_file)
                content.insert(0, line)
                break

    if not instructions:
        logging.info('\tThere is no processor instruction found. Copy as is.')
        return ''.join(content)

    # Select and apply processor by generating apropriate function
    logging.info('\tFound %s instruction(s)' % len(instructions))

    processors_count = 0
    for instruction in instructions:
        processor = get_processor(processor_name, instruction)
        if not processor:
            logging.warning('\tFAILED to define processor function for instruction %s' % instruction)
        else:
            logging.info('\t\tRunning processor %s' % processor.__name__)
            processors_count +=1
            content = processor(content)

    logging.info('\tContent was processed with %s processors' % processors_count)

    return ''.join(content)

def source_files_generator(source_dir, files):
    for filename in files:
        if filename.startswith(">>"):
            yield (filename, SourceFilesMarkup.TEXT_INSERT)
            continue

        filepath = os.path.join(source_dir, filename)
        if not os.path.exists(filepath):
            yield (filepath, SourceFilesMarkup.INVALID)
        else:
            yield (filepath, SourceFilesMarkup.FILE)


def build_artifact(project_path: str,
                   settings: configparser.ConfigParser,
                   build_config: configparser.ConfigParser,
                   version: str) -> int:
    '''Reads build configuration for particular artifacts and makes build.
        Input: project settings, artifact config, build version number
        Output: operation result (0 - success, -1 - error)
    '''

    path_prefix = ''
    if build_config.get('path'):
        path_prefix = build_config['path']
    elif settings['Paths'].get('projectPath'):
        path_prefix = settings['Paths']['projectPath']
    else:
        path_prefix = project_path
    logging.info('Path prefix: %s' % path_prefix)

    source_dir = ''
    if build_config.get('source_dir'):
        source_dir = build_config['source_dir']
    elif settings['Paths'].get('defaultSourceDir'):
        source_dir = settings['Paths']['defaultSourceDir']
    else:
        logging.error('\n[ERROR] Failed to find source dir in config!')
        return -1
    source_dir = os.path.join(path_prefix, source_dir)

    is_release = settings['General']['release'].lower() == 'yes'
    fail_on_missing_files = settings['General']['failOnMissingFiles'].lower() == 'yes'

    
    if not os.path.exists(source_dir):
        logging.error('\n[ERROR] Source directory [%s] not exists!' % source_dir)
        return -1
    logging.info('Source: %s' % source_dir)
    
    target_dir = os.path.join(
                    path_prefix,
                    settings['Paths']['releaseTo' if is_release else 'buildTo']
                )
    if not os.path.exists(target_dir):
        logging.error('\n[ERROR] Target directory [%s] not exists!' % target_dir)
        return -1

    # Adjust target directory according to artifact settings
    if build_config.get('target_dir'):
        target_dir = os.path.join(target_dir, build_config['target_dir'])
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            logging.warning('WARNING: Directories has been generated for path %s' % target_dir)

    logging.info('Target: %s' % target_dir)

    # Building
    artifact_filename = build_config.name
    artifact_full_filename = artifact_filename if is_release else '%s-%s' % (artifact_filename,version)
    artifact_full_path = os.path.join(target_dir, artifact_full_filename)

    processor_name = build_config.get('processor')

    listed_files = [f.strip() for f in build_config['order'].splitlines() if f.strip()]
    source_size = len(listed_files)
    source_files = source_files_generator(source_dir, listed_files)
    with open(artifact_full_path, 'w', encoding='utf-8') as artifact:
        artifact.write('// Version: %s\n' % (version))
        artifact.write('// Build by ezbld tool =)\n\n')

        for i, src_entry in enumerate(source_files):
            src_filename, src_type = src_entry

            if src_type == SourceFilesMarkup.INVALID:
                if fail_on_missing_files:
                    logging.error('\nBuild failed. Source file %s not exists' % src_filename)
                    return -1

                logging.warning('\nWARNING: Source file %s not exists' % src_filename)
                continue

            if src_type == SourceFilesMarkup.TEXT_INSERT:
                artifact.write(src_filename[3:-1] + "\n")
                continue

            # Otherwise - file case
            print()
            logging.info('\tFile %s/%s <%s>' % (i+1, source_size, src_filename))
            processed_content = process_file(src_filename, processor_name)

            artifact.write(processed_content)
            artifact.write('\n')

            print_progress_bar(i+1, source_size, label='\tArtifact build progress', bar_char='*')

    return 0

def load_processors(processors_settings):
    '''Loads line processors from settings file'''
    for processor_name, module_name in processors_settings.items():
        print('Loading processor [%s]...' % processor_name)
        plugin = import_module(module_name)
        plugin_processor = plugin.get()
        processors[processor_name] = plugin_processor

        print('Loaded successfully!')
    print(processors)

def main(settings_file) -> int:
    '''Entry point. Validates configs and starts building process.'''
    if not settings_file:
        settings_file = BUILD_SETTINGS

    if not os.path.exists(settings_file):
        print('\n [ERROR] Failed to find settings file (%s)' % settings_file)
        return -1

    print('Using setting file %s' % settings_file)
    settings = configparser.ConfigParser()
    settings.read(settings_file)
    project_path = ''
    if settings['Paths'].get('projectPath'):
        project_path = settings['Paths']['projectPath']
    else:
        if os.path.isabs(settings_file):
            project_path = os.path.dirname(settings_file)
        else:
            project_path = os.path.join(os.getcwd(), os.path.dirname(settings_file))

    print('Project path: %s' % project_path)

    if settings.has_section('Processors'):
        load_processors(settings['Processors'])

    build_cfg = os.path.join(project_path, settings['Files']['config'])
    if not os.path.exists(build_cfg):
        print('\n [ERROR] Failed to find build config file (%s)' % build_cfg)
        return -1

    cfg = configparser.ConfigParser()
    cfg.read(build_cfg)

    # Validation and preparation
    if not cfg.sections():
        print('\n[ERROR] Failed to read %s file! There is no sections defined!' % build_cfg)
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
        logging.info('%s of %s | Going to build artifact %s' % (idx+1, len(build_config_sections),artifact_config_name))
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

def print_progress_bar(current, limit, size=40, label='Progress', bar_char='*', empty_char=' '):
    '''Prints progress bar'''
    percentage = int(current / limit * 100)
    width = int(current / limit * size)
    progress_bar = "[%s%s]" % (
        bar_char * width,
        empty_char * (size - width)
    )

    print('{label}: {progress_bar} {percentage:>2}%'.format(label=label, progress_bar=progress_bar, percentage=percentage))


def setup_logger(settings, version):
    output_file = None
    format=None
    level = DEFAULT_LOG_LEVEL
    
    if settings.has_section('Logging'):
        if settings['Logging'].get('logToFile') and settings['Logging']['logToFile'] == 'yes':
            output_file = LOG_TO_FILE.format(
                project=os.path.basename(settings['Paths']['projectPath']),
                version=version,
                timestamp=datetime.now().strftime('%y%m%d_%H%M%S')
            )
            format=LOG_FORMAT
            
        if settings['Logging'].get('level'):
            print('Log level detected in settings file: %s' % settings['Logging']['level'].upper())
            level = settings['Logging']['level'].upper()
        
    
    logging.basicConfig(
        filename=output_file,
        encoding='utf-8',
        level=level,
        format=format
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

    BUILD_RESULT = main(args.settings_file)
    print('\n\nBuild finished with code %s' % BUILD_RESULT)
    sys.exit(BUILD_RESULT)
