import os
import sys
import pytest

sys.path.append(os.getcwd())

from processors.jspg import JSPGParser, JSPGScene, JSPGAction, JSPGParam, ParamTypes
from conftest import read_test_parameters_file


def print_comparison(expected, actual, title='Comparing'):
    print('\n\n======== %s: ========\n<Expected>:' % title)
    print(expected)
    print('                   vs\n<Actual>:')
    print(actual)


test_data_for_parse_jspg, test_ids_for_parse_jspg = read_test_parameters_file(r'tests\JSPG\files\testlist_parse_jspg_files.ini')

class TestJSPGParser:
    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\simple_scene.jspg')
    def test_parse_simple_scene(self, jspg_content):
        header, content = jspg_content

        parsed_data = JSPGParser((header, *content)).parse()
        assert parsed_data

        entity = JSPGScene.get(name=JSPGParam(header[2:].strip(), ParamTypes.TEXT))
        entity['desc'] = [
            JSPGParam('"%s"' % (''.join(content).strip()), ParamTypes.QUOTED_TEXT),
        ]
        expected_exported = JSPGScene.to_string(entity)

        print_comparison(expected_exported, parsed_data[0])
        assert parsed_data[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\actions\simple_action.jspg')
    def test_parse_simple_action(self, jspg_content):
        header, content = jspg_content

        parsed_data = JSPGParser((header, *content)).parse()
        assert parsed_data

        entity = JSPGAction.get(name=JSPGParam(header[2:].strip('\n '), ParamTypes.TEXT))
        entity['scene'] = JSPGParam(content[0].split(':')[1].strip('\n '), ParamTypes.TEXT)
        expected_exported = JSPGAction.to_string(entity)

        print_comparison(expected_exported, parsed_data[0])
        assert parsed_data[0] == expected_exported

    @pytest.mark.parametrize("input_lines", [
        '# Scene | scene\n',
        '# Scene | dialog\n',
        '# Scene | dialog | my_tag\n',
        '# Scene | dialog_left\n',
        '# Scene | dialog_right | MyTag\n'

    ])
    def test_parse_errors(self, input_lines):
        with pytest.raises(ValueError):
            JSPGParser((input_lines, )).parse()

    @pytest.mark.parametrize("jspg_file,expected_file", test_data_for_parse_jspg,
                             ids=test_ids_for_parse_jspg)
    def test_parse_jspg(self, jspg_file, expected_file, verifiable_jspg_content_parser):
        parsed_files = verifiable_jspg_content_parser(jspg_file, expected_file)
        assert len(parsed_files) > 1

        parsed_entities, verification_entities = parsed_files
        assert parsed_entities
        assert verification_entities
        for parsed, expected in zip(parsed_entities, verification_entities):
            print_comparison(expected, parsed)
            assert parsed == expected
