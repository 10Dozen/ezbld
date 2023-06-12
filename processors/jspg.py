'''Plugin for native JSPG processor'''
import re
from enum import Enum
from ezbld import ProcessorInterface

JS_INTERPOLATION_PATTERN = re.compile(r'(\${.+})')

class Modes(Enum):
    SCENE = 1
    ACTION = 2
    NESTED_ACTION = 3


class Tokens(Enum):
    PARAM = '*'
    MULTILINE = '**'
    COMMENT = '//'
    ACTION = '@ '
    SCENE = '# '
    SEPARATOR = '|'
    DESCRIPTION = '.'
    EMPTY = ''


def format_desc_block(buffer):
    '''Looks through description buffer lines and apply JS interpolation rules for it
    '''
    # Empty buffer -> empty string
    if not buffer:
        print('[JSPG][format_desc_block] Empty buffer. Exit...')
        return ''

    # Oneline buffer -> format inline interpolation
    if len(buffer) == 1:
        print('[JSPG][format_desc_block] Oneliner. Search for pattern')
        line = buffer[0]
        if JS_INTERPOLATION_PATTERN.search(line):
            print('[JSPG][format_desc_block] JS interpolation found, wrapping with `')
            line = '`%s`' % line
        line = '        "%s"' % line

        return line

    # Multiline buffer -> format multiline interpolation
    print('[JSPG][format_desc_block] Multiline. Search for pattern')
    lines = []
    for line in buffer:
        print('[JSPG][format_desc_block] Line: |%s|' % line)
        print('[JSPG][format_desc_block] Found: %s' % JS_INTERPOLATION_PATTERN.search(line))
        if JS_INTERPOLATION_PATTERN.search(line):
            line = JS_INTERPOLATION_PATTERN.sub(r'\\\1', line)
        lines.append('%s' % line)

    print('[JSPG][format_desc_block] Buffer lines:\n%s' % (buffer,))
    print('[JSPG][format_desc_block] Result lines:\n%s' % (lines,))
    print('[JSPG][format_desc_block] Lines unchanged?: %s' % (tuple(lines) == buffer,))
    
    lines[0] = '%s%s' % ('        `' if tuple(lines) == buffer else '        `>>> ', lines[0])
    lines[-1] = '%s`' % lines[-1]

    return '\n        '.join(lines)


def format_export_line(entity, key: str, export_key: str = None, ending_comma=True):
    '''Formats JSPG entity paramaeter to JS object'''
    if not export_key:
        export_key = key

    formatted = None
    if key == 'desc':
        if entity.get(key):
            lines = []
            for buffer in entity.get(key):
                lines.append(format_desc_block(buffer))
            formatted = '    "desc": [\n%s\n    ]' % (',\n'.join(lines))
        else:
            formatted = '    "desc": []'
    elif key == 'icon':
        formatted = '    "icon": %s' % entity.get(key) if entity.get(key) else ''

    elif key in ('condition', 'exec', 'pre_exec', 'post_exec', 'goto'):
        # Wrap code field with lambda function markup
        content = entity.get(key)
        if not content:
            return ''

        if not ((content.startswith('"') and content.endswith('"')) or (content.startswith("'") and content.endswith("'"))):
            content = '\n'.join(['        %s' % c for c in content.splitlines()])
            content = '() => {\n%s\n    }' % content

        formatted = '    "%s": %s' % (export_key, content)

    else:
        formatted = '    "%s": "%s"' % (export_key, entity.get(key)) if entity.get(key) else ''

    if formatted and ending_comma:
        formatted = '%s,' % formatted

    return formatted


class JSPGScene:
    '''Class to handle an JSPG Scene entity'''
    params = (
        'goto',
        'post_exec',
        'pre_exec'
    )

    @staticmethod
    def get(name: str, type: str = None, portrait: str = None):
        '''Returns pre-configured dict of JSPG Scene entity'''
        return {
            'name': name,
            'type': type,
            'portrait': portrait,
            'pre_exec': None,
            'post_exec': None,
            'goto': None,
            'desc': []
        }

    @staticmethod
    def to_string(entity: dict):
        '''Converts given dict to formatted JSPG Scene entity'''
        lines = []
        lines.append('Scenes["%s"] = {' % entity.get('name'))

        lines.append(format_export_line(entity, 'type'))
        lines.append(format_export_line(entity, 'portrait'))
        lines.append(format_export_line(entity, 'pre_exec'))
        lines.append(format_export_line(entity, 'post_exec'))
        lines.append(format_export_line(entity, 'goto'))
        lines.append(format_export_line(entity, 'desc'))
        lines.append('    "actions": []')
        lines.append('}')

        return '\n'.join([l for l in lines if l])


class JSPGAction:
    '''Class to handle an JSPG Action entity'''
    params = (
        'icon',
        'scene',
        'condition',
        'exec',
        'goto'
    )

    @staticmethod
    def get(name: str, type: str = None, portrait: str = None, tag: str = None):
        '''Returns pre-configured dict of JSPG Action entity'''
        return {
            'name': name,
            'scene': None,
            'type': type,
            'icon': None,
            'tag': tag,
            'portrait': portrait,
            'condition': None,
            'exec': None,
            'goto': None,
            'desc': []
        }

    @staticmethod
    def to_string(entity: dict):
        '''Converts given dict to formatted JSPG Action entity'''

        if not entity['scene']:
            raise ValueError('JSPG Action is missing mandatory "scene" field')

        lines = []
        lines.append('Scenes["%s"]["actions"].push({' % entity.get('scene'))

        lines.append(format_export_line(entity, 'name'))
        lines.append(format_export_line(entity, 'tag'))
        lines.append(format_export_line(entity, 'type'))
        lines.append(format_export_line(entity, 'portrait'))
        lines.append(format_export_line(entity, 'icon'))
        lines.append(format_export_line(entity, 'condition'))
        lines.append(format_export_line(entity, 'exec'))
        lines.append(format_export_line(entity, 'goto'))
        lines.append(format_export_line(entity, 'desc', ending_comma=False))
        lines.append('})')

        return '\n'.join([l for l in lines if l])


class JSPGParser:
    '''Class to parse JSPG lines into JSPG JS-objects'''
    initial_mode = None
    initial_params = None
    SECTION_PARAM_TOKENS = (Tokens.PARAM, Tokens.MULTILINE)
    parent_scene_name = None

    def __init__(self, mode: Modes, params):
        self.initial_mode = mode
        self.initial_params = params

    def parse(self, lines: list):
        '''Parses given list of lines and returns JS-compatible code'''
        # Find sections in the given lines
        sections = [{
            'start_at': 0,
            'end_at': -1,
            'mode': self.initial_mode,
            'params': self.initial_params
        }]

        for idx, line in enumerate(lines):
            token, params = self.get_section_tokens(line)

            if token == Tokens.ACTION and params:
                sections[-1]['end_at'] = idx
                sections.append({
                    'start_at': idx + 1,
                    'end_at': -1,
                    'mode': Modes.ACTION,
                    'params': params
                })
            elif token == Tokens.SCENE and params:
                sections[-1]['end_at'] = idx
                sections.append({
                    'start_at': idx + 1,
                    'end_at': -1,
                    'mode': Modes.SCENE,
                    'params': params
                })
            else:
                continue

        sections[-1]['end_at'] = len(lines)

        print('[JSPGParser] Found %s section(s)' % len(sections))
        print(sections)
        print('-' * 100)
        # ===========================================
        # Parse sections one by one

        parsed_content = []
        for idx, section in enumerate(sections):
            print('[JSPGParser] Parsing section %s: %s' % (idx, section))
            section_lines = lines[section.get('start_at'):section.get('end_at')]

            print('[JSPGParser]             there are %s line(s) in section' % len(section_lines))
            parsed_section = self.parse_section(section['mode'], section['params'], section_lines)

            print('[JSPGParser] [Finished]  Parsed content size is %s char(s)' % len(parsed_section))
            parsed_content.append(parsed_section)
            parsed_content.append('\n\n')

        print('[JSPGParser] All done!')
        return parsed_content

    @staticmethod
    def get_section_tokens(line: list):
        '''Checks for section definition and returns token and parameters of the found section'''
        line = line.strip()
        token = None
        if line.startswith(Tokens.SCENE.value):
            token = Tokens.SCENE
        elif line.startswith(Tokens.ACTION.value):
            token = Tokens.ACTION
        else:
            return (None, None)

        return (
            token,
            line[1:].strip().split(Tokens.SEPARATOR.value)
        )

    def parse_section(self, mode: Modes, params, lines: list):
        '''Parses single JSPG section'''

        # Select callable depending on mode
        entity_cls = JSPGScene if mode == Modes.SCENE else JSPGAction
        entity = entity_cls.get(*params)

        # Save scene name and re-use on following action parsing
        if mode == Modes.SCENE:
            self.parent_scene_name = entity['name']
            print('[JSPGParser][parse_section] Saved scene name for futher user => %s' % self.parent_scene_name)
        else:
            print('[JSPGParser][parse_section] Setting default *scene => %s' % self.parent_scene_name)
            entity['scene'] = self.parent_scene_name

        desc_buffer = []
        multiline_param_name = None
        multiline_param_value = []

        for idx, line in enumerate(lines):
            line = line.rstrip('\n')
            print('[JSPGParser][parse_section] %s: %s' % (idx, line))
            token, params = self.get_inline_tokens(line)
            print('[JSPGParser][parse_section] Token: %s, Params: %s' % (token, params))

            if token in self.SECTION_PARAM_TOKENS:
                # Finish and save multiline param
                if multiline_param_name:
                    print('[JSPGParser][parse_section] Saving multiline param:\n%s' % multiline_param_value)
                    # Save only if there is line with content
                    if any(l.strip('\n ') for l in multiline_param_value):
                        entity[multiline_param_name] = '\n'.join(multiline_param_value)
                        
                    multiline_param_name = None
                    multiline_param_value.clear()

                    # In case that param token serves only for closing multiline block
                    if not params:
                        continue

                # Just random string with *something... Consider it to be an desc line
                if not params:
                    print('[JSPGParser][parse_section] ...and no multiline parameter. Buffer as description')
                    desc_buffer.append(line)
                    continue

                # Read and save found param
                param_name = params[0].lower()
                param_value = params[1] if len(params) > 1 else ''

                # Check if param is allowed, otherwise consider line as description line
                if param_name not in entity_cls.params:
                    print('[JSPGParser][parse_section] Unsupported parameter [%s]' % param_name)
                    desc_buffer.append(line)
                    continue

                if token == Tokens.PARAM:
                    entity[param_name] = param_value
                else:
                    multiline_param_name = param_name
                    multiline_param_value.append(param_value)

            elif token == Tokens.COMMENT:
                # Comments to be ignored
                continue

            elif multiline_param_name:
                # No new param tokens found -> continue to gather multiline params value
                multiline_param_value.append(line)

            elif token == Tokens.EMPTY:
                # Gather data to description field
                if desc_buffer:
                    entity['desc'].append(tuple(desc_buffer))
                    desc_buffer.clear()

            elif token == Tokens.DESCRIPTION:
                # Collect description lines into buffer
                desc_buffer.append(line)
                print('[JSPGParser][parse_section] Buffer: %s' % desc_buffer)

            else:
                continue

        # Finalize multiline data gathering
        if multiline_param_name:
            entity[multiline_param_name] = '\n'.join(multiline_param_value)
        if desc_buffer:
            entity['desc'].append(tuple(desc_buffer))

        multiline_param_value.clear()
        desc_buffer.clear()

        print('[JSPGParser][parse_section] Entity:\n%s' % entity)
        print('[JSPGParser][parse_section] Entity class: %s' % entity_cls)
        print(entity_cls.to_string(entity))

        return entity_cls.to_string(entity)

    @staticmethod
    def get_inline_tokens(line: list):
        '''Read line and return apropriate token and possible parameters'''
        line = line.strip()

        if not line:
            return (Tokens.EMPTY, None)

        if line.startswith(Tokens.COMMENT.value):
            return (Tokens.COMMENT, None)

        is_param = line.startswith(Tokens.PARAM.value)
        is_multiline = line.startswith(Tokens.MULTILINE.value)

        if not is_param and not is_multiline:
            return (Tokens.DESCRIPTION, None)

        token_type = Tokens.MULTILINE if is_multiline else Tokens.PARAM
        offset_idx = 2 if is_multiline else 1

        return (
            token_type,
            [par.strip() for par in line[offset_idx:].split(':', 1) if par.strip()]
        )


# Processor functions
def jspg_proc_parse_scene(name: str, type_param: str = None):
    '''Returns processor function to parse JSPG Scene'''
    name = name.strip()
    scene_type = None
    portrait = None

    if type_param:
        nested = type_param.split()
        scene_type = nested[0].strip()
        portrait = nested[1].strip() if len(nested) > 1 else None

    def JSPG_Parse_scene(lines: list):
        parser = JSPGParser(mode=Modes.SCENE, params=(name, scene_type, portrait))
        return parser.parse(lines)

    return JSPG_Parse_scene

def jspg_proc_parse_action(name: str, type_param: str = None, tag: str = None):
    '''Returns processor function to parse JSPG Action'''
    name = name.strip()
    scene_type = None
    portrait = None

    if type_param:
        nested = type_param.split()
        scene_type = nested[0].strip()
        portrait = nested[1].strip() if len(nested) > 1 else None

    if tag:
        tag = tag.strip()

    def JSPG_Parse_action(lines: str):
        parser = JSPGParser(mode=Modes.ACTION, params=(name, scene_type, portrait, tag))
        return parser.parse(lines)

    return JSPG_Parse_action

def jspg_js_fake_named_parameters(params):
    '''Returns processor function to remove JS faked named params'''
    def JSPG_JS_Fake_named_parameters(lines: list):
        import re
        pattern = re.compile(r'\*([a-zA-Z0-9_]+)=', re.MULTILINE)
        replace_by = r'/*\1*/ '
        lines[:] = [pattern.sub(replace_by, line) for line in lines]

        return lines

    return JSPG_JS_Fake_named_parameters

class JSPGProcessor(ProcessorInterface):
    '''Provide access to JSPG processors'''
    separator = '|'
    processors = {
        '$js_fake_named_params': (jspg_js_fake_named_parameters, None),
        Tokens.SCENE.value: (jspg_proc_parse_scene, ' '),
        Tokens.ACTION.value: (jspg_proc_parse_action, ' ')
    }

    @staticmethod
    def get_definitions():
        '''Returns list of processor directives definitions'''
        return list(JSPGProcessor.processors.keys)


    @staticmethod
    def get_processor(instruction: str):
        '''Creates and returns processor function
           according to given parameters read from instruction
        '''
        params = [p.strip() for p in instruction.split(Tokens.SEPARATOR.value)]
        print("Params: %s" % params)
        instruction_type_param = params[0]
        print(list(JSPGProcessor.processors.keys()))

        for token in list(JSPGProcessor.processors.keys()):
            if instruction_type_param.startswith(token):
                processor, sep = JSPGProcessor.processors.get(token)
                if sep:
                    params[0] = sep.join(instruction_type_param.split(sep)[1:])
                print('Token: %s' % token)
                print('Param: %s' % params)
                return processor(*params)

        return None


def get() -> ProcessorInterface:
    '''Returns data needed to register processor'''
    return JSPGProcessor
