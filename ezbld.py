'''Tool for file composition (building)'''

import sys
import os
import configparser
import argparse
from importlib import import_module

BUILD_SETTINGS = 'settings.ini'

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
    version = 0
    if os.path.exists(version_track_filename):
        with open(version_track_filename, 'r', encoding='utf-8') as bvf:
            line = bvf.readline()
            version = int(line) + 1

    return version

def save_build_version(version_track_filename, version: int) -> None:
    '''Saves build version of build to the given file.
    '''
    with open(version_track_filename, 'w', encoding='utf-8') as bvf:
        bvf.write(str(version))

def process_file(filename: str, processor_name: str|None) -> str:
    '''Reads source file and checks for processor directives.
       If needed - content passed to processor for modification,
       otherwise returns file content
       Input: Filename of the source file
       Returns: string of processed content
    '''
    content = []
    with open(filename, 'r', encoding='utf-8') as src_file:
        if not processor_name or not processors.get(processor_name):
            print('\tprocess_file:> No processor name defined or'
                  f' processor for {processor_name} not found. Copy as is.')
            return src_file.read()

        # Look for processor instructions in first lines of the file.
        # If any non-empty line without instruction met
        # stop checking and consider file as a simple one
        defines = get_processor_definitions(processor_name)
        instruction = None
        search_for_instruction = True
        processor = None

        line = src_file.readline()
        while line and search_for_instruction:
            if not line:
                line = src_file.readline()
                continue

            search_for_instruction = False
            if [line for define in defines if line.lower().startswith(define.lower())]:
                instruction = line

        if not instruction:
            print('\tprocess_file:>  There is no process instruction found. Copy as is.')
            src_file.seek(0)
            return src_file.read()

        # Select and apply processor by generating apropriate function
        print(f'\tprocess_file:> Found instruction: {instruction.strip()}')
        processor = get_processor(processor_name, instruction)
        if not processor:
            print(f'\n[ERROR] Failed to define processor function for instruction {instruction}')
            return ''

        print(f'\tprocess_file:> Using processor: {processor}')
        content = processor(src_file.readlines())

    return ''.join(content)

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
    print(f'Path prefix: {path_prefix}')

    source_dir = ''
    if build_config.get('source_dir'):
        source_dir = build_config['source_dir']
    elif settings['Paths'].get('defaultSourceDir'):
        source_dir = settings['Paths']['defaultSourceDir']
    else:
        print('\n[ERROR] Failed to find source dir in config!')
        return -1
    source_dir = os.path.join(path_prefix, source_dir)

    is_release = settings['General']['release'].lower() == 'yes'
    target_dir = os.path.join(path_prefix,
                              settings['Paths']['releaseTo' if is_release else 'buildTo'] )

    print(f'Source: {source_dir}')

    if not os.path.exists(source_dir):
        print('\n[ERROR] Source directory not exists!')
        return -1
    if not os.path.exists(target_dir):
        print('\n[ERROR] Target directory not exists!')
        return -1

    # Adjust target directory according to artifact settings
    if build_config.get('target_dir'):
        target_dir = os.path.join(target_dir, build_config['target_dir'])
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            print(f'WARNING: Directories has been generated for path {target_dir}')

    print(f'Target: {target_dir}')

    source_files = []
    missing_source_files = []
    files = (f.strip() for f in build_config['order'].splitlines() if f.strip())
    for src_filename in files:
        if src_filename.startswith(">>"):
            source_files.append(src_filename)
            continue

        src_file_path = os.path.join(source_dir, src_filename)
        if not os.path.exists(src_file_path):
            print(f'\n[ERROR] Source file {src_file_path} not exists')
            missing_source_files.append(src_file_path)
        else:
            source_files.append(src_file_path)

    if missing_source_files:
        return -1

    # Building
    artifact_filename = build_config.name
    artifact_full_filename = artifact_filename if is_release else f'{artifact_filename}-{version}'
    artifact_full_path = os.path.join(target_dir, artifact_full_filename)

    processor_name = build_config.get('processor')

    source_size = len(source_files)
    with open(artifact_full_path, 'w', encoding='utf-8') as artifact:
        artifact.write(f'// Version: {version}\n')
        artifact.write('// Build by ezbld tool =)\n\n')

        for i, src_filename in enumerate(source_files):
            # Direct text injection case: >>'Some string'
            if src_filename.startswith(">>"):
                artifact.write(src_filename[3:-1] + "\n")
                continue

            # File case
            print(f'\n\tFile {i+1}/{source_size} <{src_filename}>')
            processed_content = process_file(src_filename, processor_name)

            artifact.write(processed_content)
            artifact.write('\n')

            print_progress_bar(i+1, source_size, size=50,
                               label='\tArtifact build progress', bar_char='*')

    return 0

def load_processors(processors_settings):
    '''Loads line processors from settings file'''
    for processor_name, module_name in processors_settings.items():
        print(f'Loading processor [{processor_name}]...')
        plugin = import_module(module_name)
        plugin_processor = plugin.get()
        processors[processor_name] = plugin_processor

        print('Loaded successfully!')
    print(processors)

def main(settings_file) -> int:
    '''Entry point. Validates configs and starts building process.'''
    print(settings_file)
    if not settings_file:
        settings_file = BUILD_SETTINGS

    print(settings_file)
    if not os.path.exists(settings_file):
        print(f'\n [ERROR] Failed to find settings file ({settings_file})')
        return -1

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

    print(f'Project path: {project_path}')

    if settings.has_section('Processors'):
        load_processors(settings['Processors'])

    build_cfg = os.path.join(project_path, settings['Files']['config'])
    if not os.path.exists(build_cfg):
        print(f'\n [ERROR] Failed to find build config file ({build_cfg})')
        return -1

    cfg = configparser.ConfigParser()
    cfg.read(build_cfg)

    # Validation and preparation
    if not cfg.sections():
        print(f'\n[ERROR] Failed to read {build_cfg} file! There is no sections defined!')
        return -1

    version_tracker_filename = os.path.join(project_path, settings['Files']['VersionTracker'])
    version = get_last_build_version(version_tracker_filename)
    full_version = '.'.join((
        str(settings["Version"]["major"]),
        str(settings["Version"]["minor"]),
        str(settings["Version"]["patch"]),
        str(version)
    ))
    print(f'Full version of the build: {full_version}')

    build_config_sections = cfg.sections()
    for idx, artifact_config_name in enumerate(build_config_sections):
        build_config = cfg[artifact_config_name]
        print('=' * 80)
        print(f'{idx + 1} of {len(build_config_sections)} |'
              f' Going to build artifact {artifact_config_name}')
        print('=' * 80)

        op_result = build_artifact(project_path, settings, build_config, full_version)
        if op_result < 0:
            print('\n[ERROR] Failed to build artifact. Programm stopped')
            return -1

        print()
        print_progress_bar(idx+1, len(build_config_sections),
                           size=59, label='Overall build progress')

    print('All done!')
    save_build_version(version_tracker_filename, version)

    return 0

def print_progress_bar(current, limit, size=50, label='Progress', bar_char='*', empty_char=' '):
    '''Prints progress bar'''
    percentage = int(current / limit * 100)
    width = int(current / limit * size)
    progress_bar = f"[{bar_char * width}{empty_char * (size - width)}]"

    print(f'{label}: {progress_bar} {percentage:>2}%')

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
    print(f'\n\nBuild finished with code {BUILD_RESULT}')
    sys.exit(BUILD_RESULT)
