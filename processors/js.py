'''Plugin for native JavaScript processor'''
from ezbld import ProcessorInterface

def add_indent(lines, indent=4):
    prefix = ' '*indent
    lines[:] = ['%s%s' % (prefix, line) for line in lines]


def js_proc_wrap_function(directives):
    '''Wraps content in JS function definition
    '''
    # //@wrap:function:FunctionName:FunctionParams...
    function_name = directives[2]
    function_params = directives[3]

    def JS_Wrap_to_function(lines):
        add_indent(lines)
        lines.insert(0, '%s = function (%s) {\n' % (function_name, function_params))
        lines.append('}\n')
        return lines

    return JS_Wrap_to_function

def js_proc_wrap_closure(directives):
    '''Wraps content in JS closure definition (e.g. new (function (){...})())'''
    # //@wrap:closure:FunctionName:FunctionParams...
    function_name = directives[2]
    function_params = directives[3]

    def JS_Wrap_to_closure(lines):
        add_indent(lines)
        lines.insert(0, '%s = new (function (%s) {\n' % (
            function_name,
            function_params
        ))
        lines.append('})()\n')
        return lines

    return JS_Wrap_to_closure

def js_proc_wrap_object(directives):
    '''Wraps content in JS object definitnion'''
    # //@wrap:object:NameOfObject
    object_name = directives[2]

    def JS_Wrap_to_object(lines: list):
        add_indent(lines)
        lines.insert(0, '%s = {\n' % object_name)
        lines.append('}\n')
        return lines

    return JS_Wrap_to_object

def js_proc_map(directives):
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
    map_name = directives[1].strip()
    left_obj = directives[2].strip()
    right_obj = directives[3].strip()

    def JS_Map(lines):
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

    return JS_Map

def js_proc_inline_fake_named_parameters(directives):
    def JS_Inline_fake_named_parameters(lines):
        import re
        pattern = re.compile(r'\*([a-zA-Z0-9_]+)=', re.MULTILINE)
        replace_by = r'/*\1*/ '
        lines[:] = [pattern.sub(replace_by, line) for line in lines]

        return lines

    return JS_Inline_fake_named_parameters

js_processor = {
    'prefix': '//@',
    'separator': ':',
    'types': {
        'wrap': {
            'function': js_proc_wrap_function,
            'closure': js_proc_wrap_closure,
            'object': js_proc_wrap_object
        },
        'map': js_proc_map,
        'inline': {
            'fake_named_params': js_proc_inline_fake_named_parameters
        }
    }
}

class JSProcessor(ProcessorInterface):
    '''Provide access to JavaScript processors'''
    @staticmethod
    def get_definitions():
        '''Returns list of processor directives definitions'''
        prefix = js_processor['prefix']
        return ['%s%s' % (prefix, type) for type in list(js_processor['types'])]

    @staticmethod
    def get_processor(instruction: str):
        '''Creates and returns processor function
            according to given parameters read from directive
        '''
        params = instruction[len(js_processor['prefix']):].strip().split(js_processor['separator'])

        type_param = params[0].lower()
        if not js_processor['types'].get(type_param):
            return None

        processor_type = js_processor['types'][type_param]
        subtype = params[1].lower()

        processor_func = None
        if isinstance (processor_type, dict):
            if processor_type.get(subtype):
                processor_func = processor_type[subtype]
            else:
                return None
        else:
            processor_func = processor_type

        return processor_func(params)


def get() -> ProcessorInterface:
    '''Returns data needed to register processor'''
    return JSProcessor
