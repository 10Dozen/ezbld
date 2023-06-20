import os
import sys
import pytest

sys.path.append(os.getcwd())

from processors.jspg import JSPGProcessor, js_fake_named_parameters_commenter, jspg_replace_function, Tokens, jspg_parse_function


class TestJSPGProcessor:
    @pytest.mark.parametrize("input_line,expected", [
        (
            '$js_fake_named_params\n',
            {
                "function": js_fake_named_parameters_commenter,
                "token": '$js_fake_named_params',
                "params": ['$js_fake_named_params']
            }
        ),
        (
            '$replace:KEK:LOL\n',
            {
                "function": jspg_replace_function,
                "token": '$replace',
                "params": [['KEK', 'LOL']]
            }
        ),
        (
            '$replace:KEK:\n',
            {
                "function": jspg_replace_function,
                "token": '$replace',
                "params": [['KEK', '']]
            }
        ),
        (
            '$replace:KEK\n',
            {
                "function": jspg_replace_function,
                "token": '$replace',
                "params": [['KEK']]
            }
        ),
        (
            '$replace:        KEK      :    LOL\n',
            {
                "function": jspg_replace_function,
                "token": '$replace',
                "params": [['KEK', 'LOL']]
            }
        ),
        (
            "# NewScene\n",
            {
                "function": jspg_parse_function,
                "token": Tokens.SCENE.value,
                "params": ['# NewScene']
            }
        ),
        (
            "# NewScene | scene_right\n",
            {
                "function": jspg_parse_function,
                "token": Tokens.SCENE.value,
                "params": ['# NewScene | scene_right']
            }
        ),
        (
            "@ New Action\n",
            {
                "function": jspg_parse_function,
                "token": Tokens.ACTION.value,
                "params": ['@ New Action']
            }
        ),
        (
            "@ New Action | kek\n",
            {
                "function": jspg_parse_function,
                "token": Tokens.ACTION.value,
                "params": ['@ New Action | kek']
            }
        ),
    ])
    def test_processor_selection(self, input_line, expected):
        processor = JSPGProcessor()
        result = processor.check_for_instruction(input_line)
        print(processor.instructions[0])
        assert result
        assert processor.has_instructions()
        assert processor.instructions[0] == expected

    @pytest.mark.parametrize("input_line", [
        "$replace\n",
        "$replace:\n",
        "$replace::\n",
        "$$replace\n",
        "@NewScene\n",
        "$replace_with:kek"
    ])
    def test_processor_selection_failed(self, input_line):
        processor = JSPGProcessor()
        result = processor.check_for_instruction(input_line)
        assert not result
        assert not processor.has_instructions()

    @pytest.mark.parametrize("input_lines,expected", [
        (
            (
                "$replace:A:B\n",
                "$replace:C:D\n",
                "$replace:E:F\n"
            ),
            {
                "function": jspg_replace_function,
                "token": '$replace',
                "params": [['A', 'B'], ['C', 'D'], ['E', 'F']]
            }
        ),
        (
            (
                "$replace:A:\n",
                "$replace:C:\n",
                "$replace:E\n"
            ),
            {
                "function": jspg_replace_function,
                "token": '$replace',
                "params": [['A', ''], ['C', ''], ['E']]
            }
        ),
        (
            (
                "$replace:A:B\n",
                "$replace\n",
                "$replace:\n",
                "$replace:X:Y\n",
                "$replace:X;Y\n"
            ),
            {
                "function": jspg_replace_function,
                "token": '$replace',
                "params": [['A', 'B'], ['X', 'Y'], ['X;Y']]
            }
        )
    ])
    def test_replace_processor_stacking(self, input_lines, expected):
        processor = JSPGProcessor()
        for line in input_lines:
            processor.check_for_instruction(line)
            assert processor.has_instructions()
            assert len(processor.instructions) == 1

        assert processor.instructions[0] == expected

    @pytest.mark.parametrize("input_lines,expected", [
        (
            (
                "$js_fake_named_params\n",
                "$replace:  A:  B\n",
                "$replace:  C:  D\n",
                "# NewScene\n"
            ),
            [
                {
                    "function": js_fake_named_parameters_commenter,
                    "token": '$js_fake_named_params',
                    "params": ['$js_fake_named_params']
                },
                {
                    "function": jspg_replace_function,
                    "token": '$replace',
                    "params": [['A','B'], ['C','D']]
                },
                {
                    "function": jspg_parse_function,
                    "token": Tokens.SCENE.value,
                    "params": ['# NewScene']
                },
            ]
        ),
        (
            (
                "$replace:  A:  B\n",
                "$js_fake_named_params\n",
                "$replace:  C:  D\n",
            ),
            [
                {
                    "function": jspg_replace_function,
                    "token": '$replace',
                    "params": [['A','B'], ['C','D']]
                },
                {
                    "function": js_fake_named_parameters_commenter,
                    "token": '$js_fake_named_params',
                    "params": ['$js_fake_named_params']
                },
            ]
        )
    ])
    def test_mixed_processor_selection(self, input_lines, expected):
        processor = JSPGProcessor()
        for line in input_lines:
            result = processor.check_for_instruction(line)
            assert result
            assert processor.has_instructions()

        assert processor.instructions == expected
