'''Plugin for native JavaScript processor'''
from ezbld import ProcessorInterface

def js_pp_wrap_function(directives):
    '''Wraps content in JS function definition
    '''
    # //@wrap:function:FunctionName:FunctionParams...
    function_name = directives[2]
    function_params = directives[3]

    def wrapper(lines):
        for idx, line in enumerate(lines):
            lines[idx] = f'    {line}'

        lines.insert(0, f'{function_name} = function ({function_params}) {{\n')
        lines.append('}\n')
        return lines

    return wrapper

def js_pp_wrap_closure(directives):
    '''Wraps content in JS closure definition (e.g. new (function (){...})())'''
    # //@wrap:closure:FunctionName:FunctionParams...
    function_name = directives[2]
    function_params = directives[3]

    def wrapper(lines):
        for idx, line in enumerate(lines):
            lines[idx] = f'    {line}'

        lines.insert(0, f'{function_name} = new (function ({function_params}) {{\n')
        lines.append('})()\n')
        return lines

    return wrapper

def js_pp_wrap_object(directives):
    '''Wraps content in JS object definitnion'''
    # //@wrap:object:NameOfObject
    object_name = directives[2]

    def wrapper(lines):
        for idx, line in enumerate(lines):
            lines[idx] = f'    {line}'

        lines.insert(0, f'{object_name} = {{\n')
        lines.append('}\n')
        return lines

    return wrapper

def js_pp_map(directives):
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
    map_name = directives[1]
    left_obj = directives[2]
    right_obj = directives[3]

    def wrapper(lines):
        for idx, line in enumerate(lines):
            parts = [part.strip() for part in line.split('=')]
            if len(parts) < 2:
                if line:
                    lines[idx] = f'    {line}'
                continue

            left, right = parts
            if right == '*':
                right = left

            if right_obj:
                right = f'{right_obj}.{right}'

            if left_obj:
                left = f'{left_obj}.{left}'

            lines[idx] = f'    {map_name}[{left}] = {right};\n'

        lines.insert(0, '{\n')
        lines.append('}\n')
        return lines

    return wrapper

js_processor = {
    'prefix': '//@',
    'separator': ':',
    'types': {
        'wrap': {
            'function': js_pp_wrap_function,
            'closure': js_pp_wrap_closure,
            'object': js_pp_wrap_object
        },
        'map': js_pp_map
    }
}

class JSProcessor(ProcessorInterface):
    '''Provide access to JavaScript processors'''
    @staticmethod
    def get_definitions():
        '''Returns list of processor directives definitions'''
        prefix = js_processor['prefix']
        return [f'{prefix}{type}' for type in list(js_processor['types'])]

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
