import sys
import json
import configparser
import pytest

sys.path.append(r'F:\Workstation\QSP\AxmaProjects\v2\buildtool')
from processors.jspg import JSPGScene, JSPGAction, JSPGProcessor


def pytest_configure(config):
    '''Adds custom pytest markers'''
    config.addinivalue_line(
        "markers", "jspg_file(path): set path to JSPG file content reader"
    )

@pytest.fixture
def jspg_scene_partially_configured():
    '''Returns partially configured JSPG scene entity
    '''
    e = JSPGScene.get(name='Test_Scene', entity_type='scene_right')
    e['desc'] = [
        ["Description line 1."],
        ["Description line 2."],
        ["Description line 3."]
    ]
    return e

@pytest.fixture
def jspg_scene_configured():
    '''Returns fully configured JSPG scene entity
    '''
    e = JSPGScene.get(name='Test_Scene', entity_type='dialog_right',
                      portrait='my-character.jpg')
    e['goto'] = '"Test_Scene_2"'
    e['desc'] = [
        ["Description line 1."],
        ["Description line 2."],
        ["Description line 3."]
    ]

    return e

@pytest.fixture
def jspg_action_partially_configured():
    '''Returns paritally configured JSPG action entity
    '''
    e = JSPGAction.get(name='Test action name 1',
                       entity_type='dialog_right', portrait='my-character.jpg',
                       tag='MyTag')
    e['scene'] = 'TestScene'
    e['desc'] = [
        ["Description line 1."],
        ["Description line 2."],
        ["Description line 3."]
    ]
    return e

@pytest.fixture
def jspg_action_configured():
    '''Returns fully configured JSPG action entity
    '''
    e = JSPGAction.get(name='Test action name 2',
                       entity_type='dialog_right', portrait='my-character.jpg',
                       tag='MyTag')
    e['scene'] = 'TestScene'
    e['goto'] = '"Scene2"'
    e['desc'] = [
        ["Description line 1."],
        ["Description line 2."],
        ["Description line 3."]
    ]
    return e

@pytest.fixture
def import_to_json():
    '''Returns a funtion that convert given JSPG entity to a JSON object
    '''
    def callback(exported):
        return json.loads('{%s}' % ''.join(exported.splitlines()[1:-1]))

    return callback

@pytest.fixture
def code_output_formatter():
    '''Returns a function that formats string similar to code output of JSPG parser
    '''
    prefix = '() => {'
    postfix = '    }'

    def callback(str_code):
        lines = [prefix]
        lines.extend(['        %s' % code_line for code_line in str_code.splitlines()])
        lines.append(postfix)
        return '\n'.join(lines)

    return callback

def read_jspg_file(file):
    header = ''
    content = []
    with open(file, 'r', encoding='utf-8') as f:
        header = f.readline()
        content = f.readlines()

    return header, content


@pytest.fixture
def jspg_content(request):
    '''Reads file content and return as directives line (header) and lines (content)
    '''
    path_to_file = request.node.get_closest_marker("jspg_file")
    if not path_to_file:
        return []
    return read_jspg_file(path_to_file.args[0])

@pytest.fixture
def jspg_parsed_content(jspg_content):
    header, content = jspg_content
    processor = JSPGProcessor.get_processor(header)
    if not processor:
        return

    parsed = processor(content)
    return [line for idx, line in enumerate(parsed) if idx % 2 == 0]

@pytest.fixture
def verifiable_jspg_content_parser():
    def input_data_parser(jspg_file, verification_file):
        header, content = read_jspg_file(jspg_file)
        processor = JSPGProcessor.get_processor(header)
        assert processor
        parsed_jspg = [line for idx, line in enumerate(processor(content)) if idx % 2 == 0]

        verification_entities = []
        verification_cfg = configparser.ConfigParser()
        verification_cfg.read(verification_file)
        for section_name in verification_cfg.sections():
            sec = dict(verification_cfg[section_name])
            # To adjust multiline parameret - replace \t to 4 space indent
            for key, val in sec.items():
                sec[key] = val.replace(r'\t', '    ')

            if sec.get('desc'):
                desc = []
                for block in sec['desc'].strip().split('\n\n'):
                    lines = block.split('\n')
                    desc.append(tuple(lines))

                sec['desc'] = desc

            cls_name = sec.get('cls')
            cls = globals()[sec.get('cls')]

            entity = None
            if cls_name == 'JSPGScene':
                entity = cls.get(sec.get('name'))
            else:
                entity = cls.get(sec.get('name'))

            entity.update(sec)
            verification_entities.append(cls.to_string(entity))

        return parsed_jspg, verification_entities


    return input_data_parser
