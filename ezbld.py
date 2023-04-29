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

def process_file(filename: str, processor_name) -> str:
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
                  ' processor for %s not found. Copy as is.' % (processor_name))
            return src_file.read()

        # Look for processor instructions in first lines of the file.
        # If any non-empty line without instruction met
        # stop checking and consider file as a simple one
        defines = get_processor_definitions(processor_name)
        instructions = []

        content = src_file.readlines()
        contentStartsAt = 0
        for i, line in enumerate(content):
            if not line:
                continue
            
            # If instruction line found - add to list
            # if line is not an instruction - stop futher search
            if [line for define in defines if line.lower().startswith(define)]:
                instructions.append(line)
            else:
                contentStartsAt = i
                break
                
        if not instructions:
            print('\tprocess_file:>  There is no process instruction found. Copy as is.')
            return ''.join(content)

        # Select and apply processor by generating apropriate function
        print('\tprocess_file:> Found %s instruction(s)' % len(instructions))
        
        content = content[contentStartsAt:]
        processors_count = 0
        for instruction in instructions:
            processor = get_processor(processor_name, instruction)
            if not processor:
                print('\n[ERROR] Failed to define processor function for instruction %s' % instruction)
            else:
                print('\t\tRunning processor %s' % processor.__name__)
                processors_count +=1 
                content = processor(content)

        print('\tprocess_file:> Content was processed with %s processors' % processors_count)

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
    print('Path prefix: %s' % path_prefix)

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

    print('Source: %s' % source_dir)

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
            print('WARNING: Directories has been generated for path %s' % target_dir)

    print('Target: %s' % target_dir)

    source_files = []
    missing_source_files = []
    files = (f.strip() for f in build_config['order'].splitlines() if f.strip())
    for src_filename in files:
        if src_filename.startswith(">>"):
            source_files.append(src_filename)
            continue

        src_file_path = os.path.join(source_dir, src_filename)
        if not os.path.exists(src_file_path):
            print('\n[ERROR] Source file %s not exists' % src_file_path)
            missing_source_files.append(src_file_path)
        else:
            source_files.append(src_file_path)

    if missing_source_files:
        return -1

    # Building
    artifact_filename = build_config.name
    artifact_full_filename = artifact_filename if is_release else '%s-%s' % (artifact_filename,version)
    artifact_full_path = os.path.join(target_dir, artifact_full_filename)

    processor_name = build_config.get('processor')

    source_size = len(source_files)
    with open(artifact_full_path, 'w', encoding='utf-8') as artifact:
        artifact.write('// Version: %s\n' % (version))
        artifact.write('// Build by ezbld tool =)\n\n')

        for i, src_filename in enumerate(source_files):
            # Direct text injection case: >>'Some string'
            if src_filename.startswith(">>"):
                artifact.write(src_filename[3:-1] + "\n")
                continue

            # File case
            print('\n\tFile %s/%s <%s>' % (i+1, source_size, src_filename))
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
    print(settings_file)
    if not settings_file:
        settings_file = BUILD_SETTINGS

    print(settings_file)
    if not os.path.exists(settings_file):
        print('\n [ERROR] Failed to find settings file (%s)' % settings_file)
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

    build_config_sections = cfg.sections()
    for idx, artifact_config_name in enumerate(build_config_sections):
        build_config = cfg[artifact_config_name]
        print('=' * 80)
        print('%s of %s | Going to build artifact %s' % (idx+1, len(build_config_sections),artifact_config_name))
        print('=' * 80)

        op_result = build_artifact(project_path, settings, build_config, full_version)
        if op_result < 0:
            print('\n[ERROR] Failed to build artifact. Programm stopped')
            return -1

        print()
        print_progress_bar(idx+1, len(build_config_sections),
                           size=49, label='Overall build progress')

    print('All done!')
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
