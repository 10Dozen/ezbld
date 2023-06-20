import os
import sys
import re
import json
import pytest

sys.path.append(os.getcwd())

from processors.jspg import JSPGAction, JSPGParam, ParamTypes


class TestJSPGActionEntity:
    SCENE_PARAM = JSPGParam('TestScene', ParamTypes.TEXT)
    NAME_PARAM = JSPGParam('Test action name', ParamTypes.TEXT)
    TYPE_PARAM = JSPGParam('dialog_right', ParamTypes.TEXT)
    PORTRAIT_PARAM = JSPGParam('my_character.jpg', ParamTypes.TEXT)
    TAG_PARAM = JSPGParam('MyTag', ParamTypes.TEXT)
    EXPORT_START_LINE_PATTERN = re.compile(r'Scenes\["([a-zA-Z0-9\_]*)"\]\["actions"\].push\({')

    def test_defaults(self):
        entity = JSPGAction.get(self.NAME_PARAM)

        assert entity.get("name") == self.NAME_PARAM
        assert not entity.get("type")
        assert not entity.get("portrait")
        assert not entity.get("tag")
        assert entity.get("desc") == []

    def test_custom(self):
        entity = JSPGAction.get(
            self.NAME_PARAM,
            self.TYPE_PARAM,
            self.PORTRAIT_PARAM,
            self.TAG_PARAM
        )
        entity['scene'] = self.SCENE_PARAM

        assert entity.get("scene") == self.SCENE_PARAM
        assert entity.get("name") == self.NAME_PARAM
        assert entity.get('type') == self.TYPE_PARAM
        assert entity.get('portrait') == self.PORTRAIT_PARAM
        assert entity.get('tag') == self.TAG_PARAM
        assert entity.get("desc") == []

    def test_export_partial_props(self, jspg_action_partially_configured):
        entity = jspg_action_partially_configured
        exported = JSPGAction.to_string(entity)
        print()
        print(exported)

        lines = exported.splitlines()
        scene_name_match = self.EXPORT_START_LINE_PATTERN.match(lines[0])
        assert scene_name_match
        assert scene_name_match.group(1) == entity.get('scene').value

        json_content = json.loads('{%s}' % ''.join(lines[1:-1]))
        assert json_content.get('name') == entity.get('name').value
        assert json_content.get('tag') == entity.get('tag').value
        assert json_content.get('type') == entity.get('type').value
        assert json_content.get('desc') == [param.value[1:-1] for param in entity.get('desc')]

    def test_export_full_props(self, configured_action_data):
        entity, expected = configured_action_data
        exported = JSPGAction.to_string(entity)

        print()
        print(exported)
        print('\n vs Expected:\n')
        print(expected)

        assert exported == expected

    def test_export_error_on_empty_scene(self):
        entity = JSPGAction.get(self.NAME_PARAM)
        with pytest.raises(ValueError):
            JSPGAction.to_string(entity)

