import os
import sys
import pytest

sys.path.append(os.getcwd())

from processors.jspg import JSPGProcessor, JSPGScene, JSPGAction


def print_comparison(expected, actual, title='Comparing'):
    print('\n\n======== %s: ========\n<Expected>:' % title)
    print(expected)
    print('                   vs\n<Actual>:')
    print(actual)

class TestJSPGProcessor:
    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\simple_scene.jspg')
    def test_parse_simple_scene(self, jspg_content):
        header, content = jspg_content

        processor = JSPGProcessor.get_processor(header)
        assert processor
        assert processor.__name__ == 'JSPG_Parse_scene'
        scene_data = processor(content)

        entity = JSPGScene.get('SceneSimple')
        entity['desc'] = [
            ["Some simple scene without properties."]
        ]

        expected_exported = JSPGScene.to_string(entity)
        print_comparison(expected_exported, scene_data[0])

        assert scene_data[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\actions\simple_action.jspg')
    def test_parse_simple_action(self, jspg_content):
        header, content = jspg_content

        processor = JSPGProcessor.get_processor(header)
        assert processor
        assert processor.__name__ == 'JSPG_Parse_action'

        scene_data = processor(content)

        entity = JSPGAction.get('Simple action')
        entity['scene'] = 'SceneSimple'

        expected_exported = JSPGAction.to_string(entity)
        print_comparison(expected_exported, scene_data[0])
        assert scene_data[0] == expected_exported

    @pytest.mark.parametrize("jspg_file,expected_file", [
        # Scene-file parsing
        (
            r'tests\JSPG\files\scenes\scene_and_actions.jspg',
            r'tests\JSPG\files\scenes\scene_and_actions.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_and_actions.jspg',
            r'tests\JSPG\files\scenes\scene_and_actions.expected'
        ),
        (
            r'tests\JSPG\files\scenes\multiple_scenes.jspg',
            r'tests\JSPG\files\scenes\multiple_scenes.expected'
        ),
        (
            r'tests\JSPG\files\scenes\multiple_scenes_with_actions.jspg',
            r'tests\JSPG\files\scenes\multiple_scenes_with_actions.expected'
        ),
        (
            r'tests\JSPG\files\scenes\detailed_scene.jspg',
            r'tests\JSPG\files\scenes\detailed_scene.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_with_multiline_blobs.jspg',
            r'tests\JSPG\files\scenes\scene_with_multiline_blobs.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_with_multiline_params.jspg',
            r'tests\JSPG\files\scenes\scene_with_multiline_params.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_multiline_params_on_eof.jspg',
            r'tests\JSPG\files\scenes\scene_multiline_params_on_eof.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_params_random_order.jspg',
            r'tests\JSPG\files\scenes\scene_params_random_order.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_with_comments.jspg',
            r'tests\JSPG\files\scenes\scene_with_comments.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_with_unsupported_params.jspg',
            r'tests\JSPG\files\scenes\scene_with_unsupported_params.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_with_duplicated_params.jspg',
            r'tests\JSPG\files\scenes\scene_with_duplicated_params.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_with_indents.jspg',
            r'tests\JSPG\files\scenes\scene_with_indents.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_empty.jspg',
            r'tests\JSPG\files\scenes\scene_empty.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_empty_params.jspg',
            r'tests\JSPG\files\scenes\scene_empty_params.expected'
        ),
        (
            r'tests\JSPG\files\scenes\multiple_detailed_header_scenes.jspg',
            r'tests\JSPG\files\scenes\multiple_detailed_header_scenes.expected'
        ),
        (
            r'tests\JSPG\files\scenes\scene_with_detailed_actions.jspg',
            r'tests\JSPG\files\scenes\scene_with_detailed_actions.expected'
        ),
        # Action-file parsing
        (
            r'tests\JSPG\files\actions\multiple_actions.jspg',
            r'tests\JSPG\files\actions\multiple_actions.expected'
        ),
        (
            r'tests\JSPG\files\actions\detailed_action.jspg',
            r'tests\JSPG\files\actions\detailed_action.expected'
        ),
        (
            r'tests\JSPG\files\actions\action_with_multiline_text.jspg',
            r'tests\JSPG\files\actions\action_with_multiline_text.expected'
        ),
        (
            r'tests\JSPG\files\actions\action_with_multiline_params.jspg',
            r'tests\JSPG\files\actions\action_with_multiline_params.expected'
        ),
        (
            r'tests\JSPG\files\actions\multiple_detailed_actions.jspg',
            r'tests\JSPG\files\actions\multiple_detailed_actions.expected'
        )
    ])
    def test_parse_jspg(self, jspg_file, expected_file, verifiable_jspg_content_parser):
        parsed_files = verifiable_jspg_content_parser(jspg_file, expected_file)
        assert parsed_files and len(parsed_files) > 1

        parsed_entities, verification_entities = parsed_files
        for parsed, expected in zip(parsed_entities, verification_entities):
            print_comparison(expected, parsed)
            assert parsed == expected

