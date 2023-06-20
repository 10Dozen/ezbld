'''Plugin for native JavaScript processor'''
import sys
from ezbld import ProcessorInterface


def add_indent(lines, indent=4):
    prefix = ' '*indent
    lines[:] = ['%s%s' % (prefix, line) for line in lines]


def js_proc_wrap_function(lines: list, function_name: str, function_params: str = ''):
    '''Wraps content in JS function definition'''
    # //@wrap:function:FunctionName:FunctionParams...
    add_indent(lines)
    lines.insert(0, '%s = function (%s) {\n' % (function_name, function_params))
    lines.append('}\n')

    return lines

def js_proc_wrap_closure(lines: list, function_name: str, function_params: str = ''):
    '''Wraps content in JS closure definition (e.g. new (function (){...})())'''
    # //@wrap:closure:FunctionName:FunctionParams...
    add_indent(lines)
    lines.insert(0, '%s = new (function (%s) {\n' % (
        function_name,
        function_params
    ))
    lines.append('})()\n')

    return lines

def js_proc_wrap_object(lines: list, object_name: str):
    '''Wraps content in JS object definitnion'''
    # //@wrap:object:NameOfObject
    add_indent(lines)
    lines.insert(0, '%s = {\n' % object_name)
    lines.append('}\n')

    return lines

def js_proc_map(lines: list, map_name: str, left_obj: str = '', right_obj: str = ''):
    '''Decorates content's key = value pairs with given source and target objects.
       Use cases:
       1) //@map:MapName::
           'A' = 1
           'B' = 2
           -----
           MapName['A'] = 1;
           MapName['B'] = 2;

        2) //@map:MapName:Source:Target
           KeyA = Foo
           KeyB = Bar
           -----
           MapName[Source.KeyA] = Target.Foo;
           MapName[Source.KeyB] = Target.Bar;

        3) //@map:MapName:Source:
           KeyA = 123
           KeyB = 456
           -----
           MapName[Source.KeyA] = 123;
           MapName[Source.KeyB] = 456;

        4) //@map:MapName::Target
           'A' = Foo
           'B' = Bar
           -----
           MapName['A'] = Target.Foo;
           MapName['B'] = Target.Bar;

    '''
    # //@map:MapName:SourceObject(?):TargetObject(?)
    for idx, line in enumerate(lines):
        parts = [part.strip() for part in line.split('=')]
        if len(parts) < 2:
            if line:
                lines[idx] = '    %s' % line
            continue

        left, right = parts
        if right == '*':
            right = left

        if right_obj:
            right = '%s.%s' % (right_obj, right)

        if left_obj:
            left = '%s.%s' % (left_obj, left)

        lines[idx] = '    %s[%s] = %s;\n' % (map_name, left, right)

    lines.insert(0, '{\n')
    lines.append('}\n')

    return lines

def js_proc_inline_fake_named_parameters(lines: list):
    import re
    pattern = re.compile(r'\*([a-zA-Z0-9_]+)=', re.MULTILINE)
    replace_by = r'/*\1*/ '
    lines[:] = [pattern.sub(replace_by, line) for line in lines]

    return lines


class JSProcessor(ProcessorInterface):
    '''Provide access to JavaScript processors'''
    sep = ':'
    processors = {
        '//@wrap:function:': {
            'processor': js_proc_wrap_function,
            'min_params': 1,
            'max_params': 2
        },
        '//@wrap:closure:': {
            'processor': js_proc_wrap_closure,
            'min_params': 1,
            'max_params': 2
        },
        '//@wrap:object:': {
            'processor': js_proc_wrap_object,
            'min_params': 1,
            'max_params': 1
        },
        '//@map:': {
            'processor': js_proc_map,
            'max_params': 3
        },
        '//@inline:fake_named_params': {
            'processor': js_proc_inline_fake_named_parameters,
            'max_params': 0
        }
    }

    def __init__(self):
        self.instructions = []

    def check_for_instruction(self, line: str) -> bool:
        '''Checks given line for instruction syntax and
           returns True if instruction found, otherwise False.
           Processor must save supported instruction for futher use.
        '''

        line = line.strip()
        for token, properties in self.processors.items():
            if not line.startswith(token):
                continue

            processor_data = {
                "function": properties['processor'],
                "token": token,
                "params": [],
            }

            inline_params = line[len(token):]
            params = inline_params.split(self.sep) if inline_params else []

            if not len(params) >= properties.get('min_params', 0):
                raise IndexError('Not enough number of parameters'
                                 '(%s expected, but %s was given)' % (
                    properties.get('min_params'), len(params)
                ))
            if not len(params) <= properties.get('max_params', sys.maxsize):
                raise IndexError('Too many parameters passed'
                                 '(%s expected, but %s was given)' % (
                    properties.get('max_params'), len(params)
                ))

            processor_data['params'] = params
            self.instructions.append(processor_data)
            return True

        return False

    def has_instructions(self) -> bool:
        '''Returns True if processor has any instruction found'''
        return len(self.instructions) > 0

    def process(self, content: list) -> list:
        '''Modify given content according to current instruction list'''
        for processor_data in self.instructions:
            function = processor_data.get('function')
            params = processor_data.get('params')
            content = function(content, *params)

        return content


def get() -> ProcessorInterface:
    '''Returns data needed to register processor'''
    return JSProcessor
