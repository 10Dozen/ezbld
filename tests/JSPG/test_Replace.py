import os
import sys
import pytest

sys.path.append(os.getcwd())

from processors.jspg import JSPGProcessor, js_fake_named_parameters_commenter, jspg_replace_function, Tokens, jspg_parse_function


def print_comparison(expected, actual, title='Comparing'):
    print('\n\n======== %s: ========\n<Expected>:' % title)
    print(expected)
    print('                   vs\n<Actual>:')
    print(actual)

class TestReplaceProcessor:
    @pytest.mark.parametrize("headers, content, expected", [
        (
            ("$replace:AAA:BBB\n",),
            [
                "Some text with AAA to replace\n",
                "Another AAA line with replacement option.\n"
            ],
            [
                "Some text with BBB to replace\n",
                "Another BBB line with replacement option.\n"
            ]
        ),
        (
            ("$replace:AAA:BBB\n", "$replace:XXX:YYY\n", "$replace:Agent:007\n"),
            [
                "Some text with AAA to replace\n",
                "Another XXX line with Agent option.\n"
            ],
            [
                "Some text with BBB to replace\n",
                "Another YYY line with 007 option.\n"
            ]
        ),
        (
            ("$replace:MY_DEFINE:Some\:value\n",),
            [
                "Variable of MY_DEFINE update hourly\n",
                "But this line will not change.\n"
            ],
            [
                "Variable of Some:value update hourly\n",
                "But this line will not change.\n"
            ]
        ),
        (
            ("$replace:MY_DEFINE:Value\\\:20\n",),
            [
                "Variable of MY_DEFINE update hourly\n",
                "But this line will not change.\n"
            ],
            [
                "Variable of Value\:20 update hourly\n",
                "But this line will not change.\n"
            ]
        ),
        (
            ("$replace:MY_DEFINE:FOO(BAR)\n", "$replace:BAR:1337\n"),
            [
                "Variable of MY_DEFINE update hourly\n",
                "But this line will not change.\n"
            ],
            [
                "Variable of FOO(1337) update hourly\n",
                "But this line will not change.\n"
            ]
        ),
    ])
    def test_replace_basic(self, headers, content, expected):
        processor = JSPGProcessor()
        for header in headers:
            has_instruction = processor.check_for_instruction(header)
            assert has_instruction
        print()
        print(processor.instructions)

        processed_content = processor.process(content)

        print_comparison(expected, processed_content)
        assert processed_content == expected
