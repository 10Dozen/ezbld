import os
import sys
import re
import pytest

sys.path.append(os.getcwd())
from processors.jspg import JSPGScene, JSPGParam, ParamTypes


class TestJSPGSceneEntity:
    NAME_PARAM = JSPGParam('Test_name', ParamTypes.TEXT)
    TYPE_PARAM = JSPGParam('dialog_right', ParamTypes.TEXT)
    PORTRAIT_PARAM = JSPGParam('my_character.jpg', ParamTypes.TEXT)
    EXPORT_START_LINE_PATTERN = re.compile(r'Scenes\["([a-zA-Z0-9\_]*)"\] = {')

    def test_default_params(self):
        entity = JSPGScene.get(self.NAME_PARAM)
        assert entity.get("name") == self.NAME_PARAM
        assert not entity.get("type")
        assert not entity.get("portrait")
        assert entity.get('desc') == []

    def test_custom_params(self):
        entity = JSPGScene.get(
            self.NAME_PARAM,
            self.TYPE_PARAM,
            self.PORTRAIT_PARAM
        )
        assert entity.get('name') == self.NAME_PARAM
        assert entity.get('type') == self.TYPE_PARAM
        assert entity.get('portrait') == self.PORTRAIT_PARAM
        assert entity.get('desc') == []

    def test_export_scene_name_line(self):
        entity = JSPGScene.get(self.NAME_PARAM)
        exported = JSPGScene.to_string(entity)

        scene_name_match = self.EXPORT_START_LINE_PATTERN.match(exported.splitlines()[0])
        assert scene_name_match
        assert scene_name_match.group(1) == entity.get('name').value

    def test_export_defaults(self, import_to_json):
        entity = JSPGScene.get(self.NAME_PARAM)
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
        assert json_content.get('type') == entity.get('type').value
        assert json_content.get('desc') == [param.value[1:-1] for param in entity.get('desc')]
        assert json_content.get('actions') == []

    def test_export_full_props(self, configured_jspg_scene_data):
        entity, expected = configured_jspg_scene_data
        exported = JSPGScene.to_string(entity)

        print()
        print(exported)
        print('\n vs Expected:\n')
        print(expected)
        assert exported == expected

    def test_export_multiline_text(self):
        expected_blocks = (
            '`Block1.\n        Line 1.\n        Line2.\n        Line3`',
            '`Block2.\n        Line 1.\n        Line2.\n        Line3`'
        )
        entity = JSPGScene.get(self.NAME_PARAM)
        entity['desc'] = [
            JSPGParam(['`Block1.', 'Line 1.', 'Line2.', 'Line3`'], ParamTypes.MULTILINE_TEXT),
            JSPGParam(['`Block2.', 'Line 1.', 'Line2.', 'Line3`'], ParamTypes.MULTILINE_TEXT),
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

    def test_export_multiline_code(self):
        expected = '()=>{\n        Foo.Bar()\n    }'

        entity = JSPGScene.get(self.NAME_PARAM)
        entity['pre_exec'] = JSPGParam(
            ['()=>{','    Foo.Bar()','}'],
            ParamTypes.MULTILINE_FUNCTION
        )

        exported = JSPGScene.to_string(entity)
        print(exported)
        print()

        by_comma = exported.split('\n',1)[1].split(',')
        assert len(by_comma) > 2
        block = by_comma[0].split(':')[1].strip()
        assert block == expected

    @pytest.mark.parametrize('input,expected', [
        (
            JSPGParam('Foo.Bar', ParamTypes.VARIABLE),
            'Foo.Bar'
        ),
        (
            JSPGParam('{a: 1}', ParamTypes.OBJECT),
            "{a: 1}"
        )
    ])
    def test_export_native_js_prop(self, input, expected):
        entity = JSPGScene.get(self.NAME_PARAM)
        entity['goto'] = input

        exported = JSPGScene.to_string(entity)
        print(exported)
        print()

        by_comma = exported.split('\n',1)[1].split(',')
        print(by_comma)
        assert len(by_comma) > 2
        block = by_comma[0].split(':', 1)[1].strip()
        print(block)
        assert block == expected
