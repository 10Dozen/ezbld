import sys
import re
import json
import pytest

sys.path.append(r'F:\Workstation\QSP\AxmaProjects\v2\buildtool')

from processors.jspg import JSPGAction

class TestJSPGActionEntity:
    SCENE = 'TestScene'
    NAME = 'Test action name'
    TYPE = 'dialog_right'
    PORTRAIT = 'my_character.jpg'
    TAG = 'MyTag'
    EXPORT_START_LINE_PATTERN = re.compile(r'Scenes\["([a-zA-Z0-9\_]*)"\]\["actions"\].push\({')

    def test_defaults(self):
        entity = JSPGAction.get(self.NAME)

        assert entity.get("name") == self.NAME
        assert not entity.get("type")
        assert not entity.get("portrait")
        assert not entity.get("tag")
        assert entity.get("desc") == []

    def test_custom(self):
        entity = JSPGAction.get(self.NAME, self.TYPE,
                                self.PORTRAIT, self.TAG)
        entity['scene'] = self.SCENE

        assert entity.get("scene") == self.SCENE
        assert entity.get("name") == self.NAME
        assert entity.get('type') == self.TYPE
        assert entity.get('portrait') == self.PORTRAIT
        assert entity.get('tag') == self.TAG
        assert entity.get("desc") == []

    def test_export_partial_props(self, jspg_action_partially_configured):
        entity = jspg_action_partially_configured
        exported = JSPGAction.to_string(entity)
        print()
        print(exported)

        lines = exported.splitlines()
        scene_name_match = self.EXPORT_START_LINE_PATTERN.match(lines[0])
        assert scene_name_match
        assert scene_name_match.group(1) == entity.get('scene')

        json_content = json.loads('{%s}' % ''.join(lines[1:-1]))
        assert json_content.get('name') == entity.get('name')
        assert json_content.get('tag') == entity.get('tag')
        assert json_content.get('type') == entity.get('type')
        assert json_content.get('desc') == [line[0] for line in entity.get('desc')]

    def test_export_full_props(self, jspg_action_configured):
        entity = jspg_action_configured
        exported = JSPGAction.to_string(entity)
        print()
        print(exported)

        lines = exported.splitlines()
        scene_name_match = self.EXPORT_START_LINE_PATTERN.match(lines[0])
        assert scene_name_match
        assert scene_name_match.group(1) == entity.get('scene')

        json_content = json.loads('{%s}' % ''.join(lines[1:-1]))
        assert json_content.get('name') == entity.get('name')
        assert json_content.get('tag') == entity.get('tag')
        assert json_content.get('type') == entity.get('type')
        assert json_content.get('portrait') == entity.get('portrait')
        assert json_content.get('condition') == entity.get('condition')
        assert json_content.get('exec') == entity.get('exec')
        assert json_content.get('goto') == entity.get('goto').strip('"')
        assert json_content.get('desc') == [line[0] for line in entity.get('desc')]

    def test_export_error_on_empty_scene(self):
        entity = JSPGAction.get(self.NAME)
        with pytest.raises(ValueError):
            JSPGAction.to_string(entity)

    def test_export_icon_prop(self, jspg_action_partially_configured):
        entity = jspg_action_partially_configured
        entity['icon'] = '{"img": "my-icon.png"}'

        exported = JSPGAction.to_string(entity)
        print()
        print(exported)

        lines = [l.strip() for l in exported.splitlines()]
        for line in lines:
            if line.startswith('"icon"'):
                parts = [l.strip().rstrip(',') for l in line.split(":", 1)]
                print('\nIcon property: %s' % parts)
                assert parts[1] == entity['icon']
                break

    def test_export_description_interpolation(self, jspg_action_partially_configured, import_to_json):
        EXPECTED = "`Line with interpolation ${2+2}`"

        entity = jspg_action_partially_configured
        entity['desc'] = [["Line with interpolation ${2+2}"]]

        exported = JSPGAction.to_string(entity)
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
        entity = JSPGAction.get(self.NAME)
        entity['scene'] = self.SCENE
        entity['desc'] = [
            ('Block1.', 'Line 1.', 'Line2.', 'Line3'),
            ('Block2.', 'Line 1.', 'Line2.', 'Line3')
        ]

        exported = JSPGAction.to_string(entity)
        print(exported)
        print()

        by_comma = exported.split('\n',1)[1].split(',')
        assert len(by_comma) > 2
        desc_blocks = by_comma[1:]
        first_block = desc_blocks[0].strip()[9:].strip('\n" ')
        second_block = desc_blocks[1].strip('})]\n" ')

        assert first_block == expected_blocks[0]
        assert second_block == expected_blocks[1]

    def test_export_multiline_text_with_interpolation(self):
        expected_blocks = (
            '`>>> Block1.\n        Line 1.\n        Line 2.\n        Line \${1+2}.`',
            '`>>> Block2.\n        Line \${1}.\n        Line \${2}.\n        Line \${3}.`'
        )

        entity = JSPGAction.get(self.NAME)
        entity['scene'] = self.SCENE
        entity['desc'] = [
            ('Block1.', 'Line 1.', 'Line 2.', 'Line ${1+2}.'),
            ('Block2.', 'Line ${1}.', 'Line ${2}.', 'Line ${3}.')
        ]

        exported = JSPGAction.to_string(entity)
        print(exported)
        print()

        by_comma = exported.split('\n',1)[1].split(',')
        assert len(by_comma) > 2
        desc_blocks = by_comma[1:]
        first_block = desc_blocks[0].strip()[9:].strip('\n" ')
        second_block = desc_blocks[1].strip('})]\n" ')

        assert first_block == expected_blocks[0]
        assert second_block == expected_blocks[1]

    def test_export_exec_code_prop(self, jspg_action_partially_configured):
        '''Tests formatting of code entries
        '''
        code_data = [
            '    let v = MyGame.ExecFunction()',
            '    if (v > 10) return "Lol"',
            '    return "Kek"'
        ]

        entity = jspg_action_partially_configured
        for idx, entry in enumerate(('condition', 'exec', 'goto')):
            pattern = r'"%s": \(\) => {\n\s+(.+)\n\s+(.+)\n\s+(.+)' % entry
            print('\n%s) Testing for key [%s] => pattern = %s' % (idx+1, entry, pattern))

            entity[entry] = '\n'.join(code_data)

            exported = JSPGAction.to_string(entity)
            print()
            print(exported)

            found = re.search(pattern, exported, re.MULTILINE)

            assert found
            assert len(found.groups())
            assert found.group(1) == code_data[0].strip()
            assert found.group(2) == code_data[1].strip()
            assert found.group(3) == code_data[2].strip()

            entity[entry] = None
