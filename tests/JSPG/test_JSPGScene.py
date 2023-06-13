import re
import sys
sys.path.append(r'F:\Workstation\QSP\AxmaProjects\v2\buildtool')

from processors.jspg import JSPGScene


class TestJSPGSceneEntity:
    NAME = 'Test_name'
    TYPE = 'dialog_right'
    PORTRAIT = 'my_character.jpg'
    EXPORT_START_LINE_PATTERN = re.compile(r'Scenes\["([a-zA-Z0-9\_]*)"\] = {')

    def test_default_params(self):
        entity = JSPGScene.get(self.NAME)
        assert entity.get("name") == self.NAME
        assert not entity.get("type")
        assert not entity.get("portrait")

    def test_custom_params(self):
        entity = JSPGScene.get(self.NAME, self.TYPE, self.PORTRAIT)
        assert entity.get('name') == self.NAME
        assert entity.get('type') == self.TYPE
        assert entity.get('portrait') == self.PORTRAIT

    def test_export_scene_name_line(self):
        entity = JSPGScene.get(self.NAME)
        exported = JSPGScene.to_string(entity)

        scene_name_match = self.EXPORT_START_LINE_PATTERN.match(exported.splitlines()[0])
        assert scene_name_match
        assert scene_name_match.group(1) == entity.get('name')

    def test_export_defaults(self, import_to_json):
        entity = JSPGScene.get(self.NAME)
        exported = JSPGScene.to_string(entity)

        print(exported)
        print()

        json_content = import_to_json(exported)
        assert json_content.get('desc') == []
        assert json_content.get('actions') == []

    def test_export_partial_props(self, jspg_scene_partially_configured, import_to_json):
        entity = jspg_scene_partially_configured
        exported = JSPGScene.to_string(entity)
        print()
        print(exported)

        json_content = import_to_json(exported)
        assert json_content.get('type') == entity.get('type')
        assert json_content.get('desc') == [line[0] for line in entity.get('desc')]
        assert json_content.get('actions') == []

    def test_export_full_props(self, jspg_scene_configured, import_to_json):
        entity = jspg_scene_configured
        exported = JSPGScene.to_string(entity)
        print()
        print(exported)

        json_content = import_to_json(exported)
        assert json_content.get('type') == entity.get('type')
        assert json_content.get('portrait') == entity.get('portrait')
        assert json_content.get('pre_exec') == entity.get('pre_exec')
        assert json_content.get('post_exec') == entity.get('post_exec')
        assert json_content.get('goto') == entity.get('goto').strip('"')
        assert json_content.get('desc') == [line[0] for line in entity.get('desc')]
        assert json_content.get('actions') == []

    def test_export_description_interpolation(self, jspg_scene_partially_configured, import_to_json):
        EXPECTED = "`Line with interpolation ${2+2}`"

        entity = jspg_scene_partially_configured
        entity['desc'] = [["Line with interpolation ${2+2}"]]

        exported = JSPGScene.to_string(entity)
        print()
        print(exported)

        json_content = import_to_json(exported)

        assert json_content.get('desc')
        assert json_content.get('desc')[0] == EXPECTED

    def test_export_multiline_text(self):
        expected_blocks = (
            '`Block1.\n        Line 1.\n        Line2.\n        Line3`',
            '`Block2.\n        Line 1.\n        Line2.\n        Line3`'
        )
        entity = JSPGScene.get(self.NAME)
        entity['desc'] = [
            ('Block1.', 'Line 1.', 'Line2.', 'Line3'),
            ('Block2.', 'Line 1.', 'Line2.', 'Line3')
        ]

        exported = JSPGScene.to_string(entity)
        print(exported)
        print()

        by_comma = exported.split('\n',1)[1].split(',')
        assert len(by_comma) > 2
        desc_blocks = by_comma[:-1]
        first_block = desc_blocks[0].strip()[9:].strip('\n" ')
        second_block = desc_blocks[1].strip(']\n" ')

        assert first_block == expected_blocks[0]
        assert second_block == expected_blocks[1]

    def test_export_multiline_text_with_interpolation(self):
        expected_blocks = (
            '`>>> Block1.\n        Line 1.\n        Line 2.\n        Line \${1+2}.`',
            '`>>> Block2.\n        Line \${1}.\n        Line \${2}.\n        Line \${3}.`'
        )

        entity = JSPGScene.get(self.NAME)
        entity['desc'] = [
            ['Block1.', 'Line 1.', 'Line 2.', 'Line ${1+2}.'],
            ['Block2.', 'Line ${1}.', 'Line ${2}.', 'Line ${3}.']
        ]

        exported = JSPGScene.to_string(entity)
        print(exported)
        print()

        by_comma = exported.split('\n',1)[1].split(',')
        assert len(by_comma) > 2
        desc_blocks = by_comma[:-1]
        first_block = desc_blocks[0].strip()[9:].strip('\n" ')
        second_block = desc_blocks[1].strip(']\n" ')

        assert first_block == expected_blocks[0]
        assert second_block == expected_blocks[1]

    def test_export_code_props(self, code_output_formatter):
        entity = JSPGScene.get(self.NAME)

        PROP_PRE_EXEC = "pre_exec"
        PROP_POST_EXEC = "post_exec"
        PROP_GOTO = "goto"

        entity[PROP_GOTO] = 'return \'MyScene\''
        entity[PROP_POST_EXEC] = 'MyGame.Update()\nMyGame.MC.SetCoin(100)'
        entity[PROP_PRE_EXEC] = 'MyGame.MC.PrepareToTest()'

        exported = JSPGScene.to_string(entity)
        print(exported)
        print()

        by_comma = exported.split('\n',1)[1].split(',')
        keys_to_find = (PROP_PRE_EXEC, PROP_POST_EXEC, PROP_GOTO)
        exported_data = {}

        for line in by_comma:
            tokens_in_line = line.split(':')
            if len(tokens_in_line) == 1:
                continue

            param_token, data = tokens_in_line
            param_token = param_token.strip().strip('"')
            if not param_token in keys_to_find:
                continue

            exported_data[param_token] = data.strip()

        assert exported_data[PROP_GOTO] == code_output_formatter(entity[PROP_GOTO])
        assert exported_data[PROP_PRE_EXEC] == code_output_formatter(entity[PROP_PRE_EXEC])
        assert exported_data[PROP_POST_EXEC] == code_output_formatter(entity[PROP_POST_EXEC])
