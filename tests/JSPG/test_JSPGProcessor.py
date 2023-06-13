import pytest
import sys

sys.path.append(r'F:\Workstation\QSP\AxmaProjects\v2\buildtool')

from processors.jspg import JSPGProcessor, JSPGScene, JSPGAction


def print_comparison(expected, actual, title='Comparing'):
    print('\n\n======== %s: ========\n<Expected>:' % title)
    print(expected)
    print('                   vs\n<Actual>:')
    print(actual)

class TestJSPGProcessorScene:
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

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_and_actions.jspg')
    def test_parse_scene_with_actions(self, jspg_parsed_content):
        assert jspg_parsed_content

        # Compare parsed elements
        # - Scene
        scene_entity = JSPGScene.get('SceneName')
        scene_entity['desc'] = [
            ["This is a scene."]
        ]
        scene_exported = JSPGScene.to_string(scene_entity)
        print_comparison(scene_exported, jspg_parsed_content[0])
        assert jspg_parsed_content[0] == scene_exported

        # - Action 1
        action_entity_1 = JSPGAction.get('Action 1')
        action_entity_1['scene'] = scene_entity['name']
        action_entity_1['desc'] = [
            ("This is an first action for SceneName.",)
        ]
        action_entity_1_exported = JSPGAction.to_string(action_entity_1)
        print_comparison(action_entity_1_exported, jspg_parsed_content[1])
        assert jspg_parsed_content[1] == action_entity_1_exported

        # - Action 2
        action_entity_2 = JSPGAction.get('Action 2')
        action_entity_2['scene'] = scene_entity['name']
        action_entity_2['desc'] = [
            ("This is an second action for SceneName.",)
        ]
        action_entity_2_exported = JSPGAction.to_string(action_entity_2)
        print_comparison(action_entity_2_exported, jspg_parsed_content[2])
        assert jspg_parsed_content[2] == action_entity_2_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\multiple_scenes.jspg')
    def test_parse_multiple_scenes(self, jspg_parsed_content):
        assert jspg_parsed_content
        print(jspg_parsed_content)
        print('-' * 100)

        # Compare parsed elements
        expected_scene = JSPGScene.get('Scene1')
        expected_scene['desc'] = [["This is a first scene."]]
        assert jspg_parsed_content[0] == JSPGScene.to_string(expected_scene)

        expected_scene = JSPGScene.get('Scene2')
        expected_scene['desc'] = [["This is a second scene."]]
        assert jspg_parsed_content[1] == JSPGScene.to_string(expected_scene)

        expected_scene = JSPGScene.get('Scene3')
        expected_scene['desc'] = [["This is a third scene."]]
        assert jspg_parsed_content[2] == JSPGScene.to_string(expected_scene)

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\multiple_scenes_with_actions.jspg')
    def test_parse_multilple_scenes_with_actions(self, jspg_parsed_content):
        assert jspg_parsed_content
        assert len(jspg_parsed_content) == 8

        print(jspg_parsed_content)
        print('-' * 100)

        parsed_scenes = (jspg_parsed_content[0], jspg_parsed_content[4])
        parsed_actions = (
            (
                jspg_parsed_content[1],
                jspg_parsed_content[2],
                jspg_parsed_content[3],
            ),
            (
                jspg_parsed_content[5],
                jspg_parsed_content[6],
                jspg_parsed_content[7]
            )
        )

        expected_data = (
            {
                "name": 'SceneOne',
                "desc": [["Description for SceneOne."]],
                "actions": (
                    {
                        "name": 'Action One',
                        "desc": [['Action one for SceneOne.']]
                    },
                    {
                        "name": 'Action Two',
                        "desc": [['Action two for SceneOne.']]
                    },
                    {
                        "name": 'Action Three',
                        "desc": []
                    },
                )
            },
            {
                "name": 'AnotherScene',
                "desc": None,
                "actions": (
                    {
                        "name": 'Action One',
                        "desc": [['Action one for AnotherScene.']]
                    },
                    {
                        "name": 'Action Two',
                        "desc": [['Action two for AnotherScene.']]
                    },
                    {
                        "name": 'Action Three',
                        "desc": []
                    },
                )
            }
        )

        for scene_idx, expected_scene in enumerate(expected_data):
            scene = JSPGScene.get(expected_scene['name'])
            scene['desc'] = expected_scene['desc']

            print('\n\n======== Comparing scene: ========')
            print(JSPGScene.to_string(scene))
            print('                   vs')
            print(parsed_scenes[scene_idx])

            assert parsed_scenes[scene_idx] == JSPGScene.to_string(scene)

            for action_idx, expected_action in enumerate(expected_scene['actions']):
                action = JSPGAction.get(expected_action['name'])
                action['scene'] = expected_scene['name']
                action['desc'] = expected_action['desc']

                print('\n\n======== Comparing action: ========')
                print(JSPGAction.to_string(action))
                print('                   vs')
                print(parsed_actions[scene_idx][action_idx])

                assert parsed_actions[scene_idx][action_idx] == JSPGAction.to_string(action)

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\detailed_scene.jspg')
    def test_parse_detailed_scene(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGScene.get('DetailedScene', 'dialog', 'my_character.jpg')
        expected['pre_exec'] = "MyGame.ExecutePre()"
        expected['post_exec'] = "MyGame.ExecutePost()"
        expected['goto'] = '"Scene2"'
        expected['desc'] = [
            ('This is a scene with properties.',),
            ('It should be parsed into fully configured scene entity.',)
        ]

        expected_exported = JSPGScene.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])

        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_with_multiline_blobs.jspg')
    def test_parse_scene_with_multiline_text(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGScene.get('MultilinedScene')
        expected['desc'] = [
            ('First multiline block.', 'Line 1/1.', 'Line 1/2.'),
            ('Second multiline block.', 'Line ${2/1}.', 'Line ${2/2}.')
        ]
        expected_exported = JSPGScene.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])

        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_multiline_params.jspg')
    def test_parse_scene_with_multiline_params(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGScene.get('SceneWithMultilineParams')
        expected['pre_exec'] = ("\n"
                                "    MyGame.PreExec()\n"
                                "    if (MyGame.State() == States.OK) {\n"
                                "        MyGame.Activate()\n"
                                "    } else {\n"
                                "        MyGame.VerifyLoadedFile()\n"
                                "    }")
        expected['post_exec'] = ("\n"
                                 "    MyGame.SetSceneResult(1, true)\n"
                                 "    JSPG.GoTo('Scene3')")
        expected['goto'] = ("\n"
                            "    return MyGame.SelectScene()")
        expected['desc'] = [('Some description line.',)]

        expected_exported = JSPGScene.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])

        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_multiline_params_on_eof.jspg')
    def test_parse_scene_with_multiline_params_on_eof(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGScene.get('SceneMultilineParamsOnEOF')
        expected['desc'] = [
            ('Line 1.', ),
            ('Line ${Foo.Bar()}.',)
        ]
        expected['post_exec'] = ("\n"
                                 "    JSPG.GoTo('NormalScene')")

        expected_exported = JSPGScene.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])

        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_params_random_order.jspg')
    def test_parse_scene_params_random_order(self, jspg_parsed_content):
        assert jspg_parsed_content
        expected = JSPGScene.get('SceneParamsRandomOrder')
        expected['pre_exec'] = ("\n"
                                "    let foo = bar()\n"
                                "    foo.update(10)")
        expected['post_exec'] = 'Foo.Bar()'
        expected['goto'] = '"Scene2"'
        expected['desc'] = [
            ('Text line in the beginning.', ),
            ('Text line between params.', ),
            ('Final text line here.', ),
        ]

        expected_exported = JSPGScene.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])

        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_with_comments.jspg')
    def test_parse_scene_with_comments(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGScene.get('SceneWithComments')
        expected['post_exec'] = ("\n"
                                 "    Bar.Foo()")
        expected['desc'] = [
            ('Line 1.',),
            ('Block 1.', 'Line 1-1.', 'Line 1-3.'),
        ]
        expected_exported = JSPGScene.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])
        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_with_unsupported_params.jspg')
    def test_parse_scene_with_unsupported_params(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGScene.get('SceneWithUnsupportedParams', 'title')
        expected['desc'] = [
            ('Desc line 1.', ),
            ('*', ),
            ('*portrait: picture.jpg', ),
            ('**', ),
            ('Desc line 5.', ),
            ('*Desc line 6.', ),
            ('**Desc line 7.', ),
        ]
        expected_exported = JSPGScene.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])

        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_with_duplicated_params.jspg')
    def test_parse_scene_with_duplicated_params(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGScene.get("SceenWithDuplicatedParams")
        expected['goto'] = '"Scene1"'
        expected['desc'] = [
            ('Some line.', ),
            ('Some line again.', )
        ]
        expected_exported = JSPGScene.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])
        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_with_indents.jspg')
    def test_parse_scene_with_indents(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGScene.get("SceneWithIndents")
        expected['goto'] = '"Scene2"'
        expected['pre_exec'] = 'Foo.Bar()'
        expected['desc'] = [
            ('Desc line 1. ', ),
            ('   Desc line 2.   ', ),
            ('         Desc line 3.', ),
        ]
        expected_exported = JSPGScene.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])
        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_empty.jspg')
    def test_parse_scene_empty(self, jspg_parsed_content):
        assert jspg_parsed_content

        for idx, name in enumerate(('EmptyScene', 'EmptyScene2', 'AnotherEmpty')):
            expected = JSPGScene.get(name)
            expected_exported = JSPGScene.to_string(expected)
            print_comparison(expected_exported, jspg_parsed_content[idx])
            assert jspg_parsed_content[idx] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\scenes\scene_empty_params.jspg')
    def test_parse_scene_empty_params(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGScene.get('SceneWithEmptyParams')
        expected['desc'] = [
            ('Desc line 1.', ),
            ('Desc line 2.', ),
        ]
        expected_exported = JSPGScene.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])

        assert jspg_parsed_content[0] == expected_exported


class TestJSPGProcessorActions:
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

    @pytest.mark.jspg_file(r'tests\JSPG\files\actions\multiple_actions.jspg')
    def test_parse_multiple_actions(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected_scene_name = 'SceneName'
        expected_action_data = (
            {
                "name": 'Action One',
                "desc": [('This is action one content.',)]
            },
            {
                "name": 'Action Two',
                "desc": [('This is action two content.',)]
            },
            {
                "name": 'Action Three',
                "desc": [('This is action three content.',)]
            },
        )

        for idx, expected_data in enumerate(expected_action_data):
            action = JSPGAction.get(expected_data['name'])
            action['scene'] = expected_scene_name
            action['desc'] = expected_data['desc']
            action_exported = JSPGAction.to_string(action)
            print_comparison(action_exported, jspg_parsed_content[idx])
            assert jspg_parsed_content[idx] == action_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\actions\detailed_action.jspg')
    def test_parse_detailed_action(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGAction.get('Detailed Action', 'dialog_right', 'mypic.jpg', 'MyTag')
        expected['scene'] = "CurrentScene"
        expected['icon'] = '{img: my_picture.jpg}'
        expected['condition'] = '"Foo.Bar"'
        expected['exec'] = ("\n"
                            "    let foo = bar()\n"
                            "    foo.update(100)")
        expected['goto'] = '"SceneAnother"'
        expected['desc'] = [("Some line of description.",)]

        expected_exported = JSPGAction.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])
        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\actions\action_with_multiline_text.jspg')
    def test_parse_action_with_multiline_text(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGAction.get('Action with multiline text', 'scene_right', None, 'MyTag')
        expected['scene'] = 'CurrentScene'
        expected['goto'] = '"Scene2"'
        expected['desc'] = [
            ('Block 1.', 'Line 1.', 'Line 2.'),
            ('Block 2.', 'Line ${1}.', 'Line ${2}.'),
            ('Line ${3}',)
        ]

        expected_exported = JSPGAction.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])
        assert jspg_parsed_content[0] == expected_exported

    @pytest.mark.jspg_file(r'tests\JSPG\files\actions\action_with_multiline_params.jspg')
    def test_parse_action_with_multiline_params(self, jspg_parsed_content):
        assert jspg_parsed_content

        expected = JSPGAction.get('Action with multiline params', None, None, 'MyTag')
        expected['scene'] = 'CurrentScene'
        expected['icon'] = "{text: 'A', class: 'icon-button-red'}"
        expected['goto'] = ('\n'
                            '    Foo.Bar()\n'
                            '    return Foo.GetNextScene()')
        expected['condition'] = ('\n'
                                 '    if (Foo.Bar()) return true\n'
                                 '    return Foo.CheckOtherCondition()')
        expected['exec'] = ('\n'
                            '    Player.AddXP(1000)\n'
                            '    Player.AddMoney(500)\n'
                            '    GUI.UpdatePlayerInfo()')

        expected_exported = JSPGAction.to_string(expected)
        print_comparison(expected_exported, jspg_parsed_content[0])
        assert jspg_parsed_content[0] == expected_exported
