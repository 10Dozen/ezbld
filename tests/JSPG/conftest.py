import sys
import json
import configparser
import pytest

sys.path.append(r'F:\Workstation\QSP\AxmaProjects\v2\buildtool')
from processors.jspg import JSPGParser, JSPGScene, JSPGAction, JSPGParam, ParamTypes


def pytest_configure(config):
    '''Adds custom pytest markers'''
    config.addinivalue_line(
        "markers", "jspg_file(path): set path to JSPG file content reader"
    )

@pytest.fixture
def jspg_scene_partially_configured():
    '''Returns partially configured JSPG scene entity
    '''
    e = JSPGScene.get(
        name=JSPGParam('Test_Scene', ParamTypes.TEXT),
        entity_type=JSPGParam('scene_right', ParamTypes.TEXT)
    )

    e['desc'] = [
        JSPGParam('"Description line 1."', ParamTypes.QUOTED_TEXT),
        JSPGParam('"Description line 2."', ParamTypes.QUOTED_TEXT),
        JSPGParam('"Description line 3."', ParamTypes.QUOTED_TEXT)
    ]
    return e

@pytest.fixture
def configured_jspg_scene_data():
    '''Returns fully configured JSPG scene entity
    '''
    e = JSPGScene.get(
        name=JSPGParam('Test_Scene', ParamTypes.TEXT),
        entity_type=JSPGParam('dialog_right', ParamTypes.TEXT),
        portrait=JSPGParam('my-character.jpg', ParamTypes.TEXT)
    )
    e['goto'] = JSPGParam('Test_Scene_2', ParamTypes.TEXT)
    e['pre_exec'] = JSPGParam('()=>{ Foo.Bar() }', ParamTypes.FUNCTION)
    e['post_exec'] = JSPGParam('()=>{ Bar.Foo() }', ParamTypes.FUNCTION)
    e['desc'] = [
        JSPGParam('"Description line 1."', ParamTypes.QUOTED_TEXT),
        JSPGParam('"Description line 2."', ParamTypes.QUOTED_TEXT),
        JSPGParam('"Description line 3."', ParamTypes.QUOTED_TEXT)
    ]

    expected = ('Scenes["Test_Scene"] = {\n'
        '    "type": "dialog_right",\n'
        '    "portrait": "my-character.jpg",\n'
        '    "pre_exec": ()=>{ Foo.Bar() },\n'
        '    "post_exec": ()=>{ Bar.Foo() },\n'
        '    "goto": "Test_Scene_2",\n'
        '    "desc": [\n'
        '        "Description line 1.",\n'
        '        "Description line 2.",\n'
        '        "Description line 3."\n'
        '    ],\n'
        '    "actions": []\n'
        '}'
    )

    return e, expected

@pytest.fixture
def jspg_action_partially_configured():
    '''Returns paritally configured JSPG action entity
    '''
    e = JSPGAction.get(
        name=JSPGParam('Test action name 1', ParamTypes.TEXT),
        entity_type=JSPGParam('dialog_right', ParamTypes.TEXT),
        portrait=JSPGParam('my-character.jpg', ParamTypes.TEXT),
        tag=JSPGParam('MyTag', ParamTypes.TEXT)
    )
    e['scene'] = JSPGParam('TestScene', ParamTypes.TEXT)
    e['desc'] = [
        JSPGParam('"Description line 1."', ParamTypes.QUOTED_TEXT),
        JSPGParam('"Description line 2."', ParamTypes.QUOTED_TEXT),
        JSPGParam('"Description line 3."', ParamTypes.QUOTED_TEXT)
    ]
    return e

@pytest.fixture
def configured_action_data():
    '''Returns fully configured JSPG action entity
    '''
    e = JSPGAction.get(
        name=JSPGParam('Test action name 2', ParamTypes.TEXT),
        entity_type=JSPGParam('dialog_right', ParamTypes.TEXT),
        portrait=JSPGParam('my-character.jpg', ParamTypes.TEXT),
        tag=JSPGParam('MyTag', ParamTypes.TEXT)
    )
    e['scene'] = JSPGParam('TestScene', ParamTypes.TEXT)
    e['tag'] = JSPGParam('MyTag', ParamTypes.TEXT)
    e['goto'] = JSPGParam('Scene2', ParamTypes.TEXT)
    e['condition'] = JSPGParam('()=>{ return Test.Foo() }', ParamTypes.FUNCTION)
    e['exec'] = JSPGParam('()=>{ Foo.Bar() }', ParamTypes.FUNCTION)
    e['desc'] = [
        JSPGParam('"Description line 1."', ParamTypes.QUOTED_TEXT),
        JSPGParam('"Description line 2."', ParamTypes.QUOTED_TEXT),
        JSPGParam('"Description line 3."', ParamTypes.QUOTED_TEXT)
    ]

    expected = ('Scenes["TestScene"]["actions"].push({\n'
        '    "name": "Test action name 2",\n'
        '    "tag": "MyTag",\n'
        '    "type": "dialog_right",\n'
        '    "portrait": "my-character.jpg",\n'
        '    "condition": ()=>{ return Test.Foo() },\n'
        '    "exec": ()=>{ Foo.Bar() },\n'
        '    "goto": "Scene2",\n'
        '    "desc": [\n'
        '        "Description line 1.",\n'
        '        "Description line 2.",\n'
        '        "Description line 3."\n'
        '    ]\n'
        '})'
    )

    return e, expected

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

def read_test_parameters_file(file):
    '''Reads ini file with sections that contins list of parameters for tests.
       Section name is used as ID, 'params' value - converted to tuple '''
    config = configparser.ConfigParser()
    config.read(file)

    ids = []
    output = []
    for section_name in config.sections():
        sec = config[section_name]
        if sec.getboolean('skip', False):
            continue

        ids.append(section_name)
        params = [p for p in sec.get('params').split() if p.strip()]
        output.append(tuple(params))

    return output, ids

@pytest.fixture
def jspg_content(request):
    '''Reads file content and return as directives line (header) and lines (content)
    '''
    path_to_file = request.node.get_closest_marker("jspg_file")
    if not path_to_file:
        return []
    return read_jspg_file(path_to_file.args[0])

@pytest.fixture
def verifiable_jspg_content_parser():
    def input_data_parser(jspg_file, verification_file):
        header, content = read_jspg_file(jspg_file)
        parsed_data = JSPGParser((header, *content)).parse()
        assert parsed_data
        parsed_jspg = [line for idx, line in enumerate(parsed_data) if idx % 2 == 0]

        verification_entities = []
        verification_cfg = configparser.ConfigParser()
        verification_cfg.read(verification_file)
        for section_name in verification_cfg.sections():
            # sec = dict(verification_cfg[section_name])
            sec = verification_cfg[section_name]
            entity_params = dict()

            for key, val in sec.items():
                if key == 'cls':
                    continue

                # To adjust multiline parameret - replace \t to 4 space indent
                val = val.replace(r'\t', '    ')

                # Create JSPGParam from descriptors
                parts = [v.strip() for v in val.split('|')]
                if len(parts) > 1:
                    param_value = parts[0]
                    param_type = globals()['ParamTypes'].__members__.get(parts[1])
                    if param_type == ParamTypes.MULTILINE_FUNCTION:
                        param_value = parts[0].split('\n')

                    val = JSPGParam(param_value, param_type)

                entity_params[key] = val

            if sec.get('desc'):
                desc = []
                blocks = sec['desc'].strip().split('\n\n')
                for block in blocks:
                    lines = block.split('\n')

                    if len(lines) == 1:
                        param = ParamTypes.QUOTED_TEXT
                        line = block
                    else:
                        param = ParamTypes.MULTILINE_TEXT
                        line = lines

                    desc.append(JSPGParam(line, param))

                entity_params['desc'] = desc

            cls = globals()[sec.get('cls')]
            entity = cls.get(entity_params.get('name'))

            entity.update(entity_params)
            verification_entities.append(cls.to_string(entity))

        return parsed_jspg, verification_entities


    return input_data_parser
