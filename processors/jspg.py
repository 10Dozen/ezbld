'''Plugin for JSPG processor'''
import re
import logging
from enum import Enum
from dataclasses import dataclass
from ezbld import ProcessorInterface


class Modes(Enum):
    '''Possible modes of parser'''
    SCENE = 1
    ACTION = 2

class Tokens(Enum):
    '''Tokens to be recognized by parser and processor'''
    PARAM = '*'
    MULTILINE = '**'
    COMMENT = '//'
    ACTION = '@ '  # With whitespace!
    SCENE = '# '   # With whitespace!
    SEPARATOR = '|'
    # Values will never be used
    DESCRIPTION = -1
    EMPTY = 0

class TypeTokens(Enum):
    '''Shortcut tokens for entity type definition'''
    SCENE_CENTER = '^'
    SCENE_LEFT = '<'
    SCENE_RIGHT = '>'
    DIALOG_LEFT = '<#'
    DIALOG_RIGHT = '#>'
    TITLE = 'T'
    SUBTITLE = 'ST'
    CONTAINER = 'C'
    HIDDEN = 'HID'

    @staticmethod
    def match(value):
        '''Return TypeToken entity that match given value.'''
        return TypeTokens._value2member_map_.get(value)

class ParamTypes(Enum):
    '''Type of parameter value. Used as hint during export to JS'''
    TEXT = 0
    QUOTED_TEXT = 1
    MULTILINE_TEXT = 2
    VARIABLE = 20
    FUNCTION = 30
    MULTILINE_FUNCTION = 31
    OBJECT = 40


def format_export_line(entity, key: str, export_key: str = None, ending_comma=True):
    '''Formats JSPG entity parameter to JS object syntax'''
    param = entity.get(key)
    if not param:
        # 'desc' is mandatory param for JSPG, so it should always be formatted
        return '    "desc": [],' if key == 'desc' else ''

    if not export_key:
        export_key = key
    logging.debug('Exporting key=%s to export key=%s', key, export_key)
    logging.debug('   Exporting param: %s', param)

    formatted = None
    if key == 'desc':
        # Desc is a collection of params representing one blob.
        logging.debug('      Exporting descriptions')
        lines = []
        for blob in param:
            if blob.type == ParamTypes.MULTILINE_TEXT:
                lines.append('\n'.join(['        %s' % l for l in blob.value]))
            else:
                lines.append('        %s' % blob.value)
        formatted = '    "desc": [\n%s\n    ]' % (',\n'.join(lines))
    else:
        logging.debug('      Exporting other parameters')
        if param.type == ParamTypes.TEXT:
            formatted = '    "%s": "%s"' % (export_key, param.value)
        elif param.type == ParamTypes.MULTILINE_FUNCTION:
            formatted = '    "%s": %s' % (
                export_key,
                '\n    '.join(['%s' % l for l in param.value])
            )
        else:
            formatted = '    "%s": %s' % (export_key, param.value)

    if formatted and ending_comma:
        formatted = '%s,' % formatted

    return formatted

@dataclass
class JSPGParam:
    '''Represents single param value of JSPG Entity'''
    value: str
    type: ParamTypes = ParamTypes.TEXT


class JSPGScene:
    '''Class to handle an JSPG Scene entity'''
    params = (
        'goto',
        'post_exec',
        'pre_exec'
    )

    @staticmethod
    def get(name: JSPGParam, entity_type: JSPGParam = None, portrait: JSPGParam = None):
        '''Returns pre-configured dict of JSPG Scene entity'''
        return {
            'name': name,
            'type': entity_type,
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
        lines.append('Scenes["%s"] = {' % entity['name'].value)
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
    def get(name: JSPGParam, entity_type: JSPGParam = None, portrait: JSPGParam = None, tag: JSPGParam = None):
        '''Returns pre-configured dict of JSPG Action entity'''
        return {
            'name': name,
            'scene': None,
            'type': entity_type,
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
            exception = ValueError('JSPG Action is missing mandatory "scene" field')
            logging.critical(exception)
            logging.critical('Failed entity: %s', entity)
            raise exception

        lines = []
        lines.append('Scenes["%s"]["actions"].push({' % entity['scene'].value)
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
    SECTION_PARAM_TOKENS = (Tokens.PARAM, Tokens.MULTILINE)
    JS_INTERPOLATION_PATTERN = re.compile(r'(\${.+})')
    MULTILINE_CODE_PARAMS = ("goto", "pre_exec", "post_exec", "condition", "exec")

    def __init__(self, lines: list):
        self.lines = lines
        self.parent_scene_name = None
        self.possible_goto = None

    def parse(self):
        '''Parses given list of lines and returns JS-compatible code'''

        # Scan for sections (scene or action definitions)
        sections = []
        eof_idx = len(self.lines)
        for idx, line in enumerate(self.lines):
            token, mode, params = self.get_section_tokens(line)
            logging.debug('Line %s: [%s] -> token: %s, mode: %s, params: %s',
                          idx, line, token, mode, params)

            if not token or not params:
                logging.debug('No token. Skip line...')
                continue

            if sections:
                logging.debug('End of previous section is set to %s', idx)
                sections[-1]['end_at'] = idx

            sections.append({
                'start_at': idx + 1,
                'end_at': eof_idx,
                'mode': mode,
                'params': params
            })
            logging.debug('Adding section: %s', sections[-1])

        logging.debug('Found %s section(s)', len(sections))
        logging.debug(sections)
        logging.debug('-' * 100)
        # ===========================================
        # Parse sections one by one

        parsed_content = []
        for idx, section in enumerate(sections):
            section_lines = self.lines[section.get('start_at'):section.get('end_at')]
            logging.debug('Parsing section %s: %s', idx, section)

            # If case actions is followed by scene - assume thath action may lead to it.
            # Name of the next scene will be applied as default 'goto' for action,
            # until '*goto' param overrides it.
            if section['mode'] == Modes.ACTION and not self.possible_goto:
                self.possible_goto = next(
                    (self.parse_param(sec['params'][0], 'goto')
                     for sec in sections[idx+1:]
                     if sec['mode'] == Modes.SCENE),
                    None
                )
            else:
                # If Scene is parsed - drop possible_goto to avoid recursive links
                self.possible_goto = None

            parsed_section = self.parse_section(section['mode'], section['params'], section_lines)

            logging.debug('[Finished]  Parsed content size is %s char(s)', len(parsed_section))
            parsed_content.append(parsed_section)
            parsed_content.append('\n\n')

        logging.debug('All done!')
        return parsed_content

    @staticmethod
    def get_section_tokens(line: str):
        '''Checks for section definition and returns token and parameters of the found section'''
        line = line.strip()
        token = None
        mode = None
        if line.startswith(Tokens.SCENE.value):
            token = Tokens.SCENE
            mode = Modes.SCENE
        elif line.startswith(Tokens.ACTION.value):
            token = Tokens.ACTION
            mode = Modes.ACTION
        else:
            return (None, None, None)

        params = [p.strip() for p in line[1:].split(Tokens.SEPARATOR.value)]
        return (token, mode, params)

    def parse_section(self, mode: Modes, params: list, lines: list):
        '''Parses single JSPG section'''

        # Select callable depending on mode
        entity_cls = JSPGScene if mode == Modes.SCENE else JSPGAction
        entity_params = self.parse_section_params(entity_cls, params)
        entity = entity_cls.get(*entity_params)

        # Save scene name and re-use on following action parsing
        if mode == Modes.SCENE:
            self.parent_scene_name = entity['name']
            logging.debug('Scene parsing. Save scene name for futher user => %s',
                          self.parent_scene_name)
        else:
            logging.debug('Action parsing. Setting default *scene => %s', self.parent_scene_name)
            entity['scene'] = self.parent_scene_name
            logging.debug('Action parsing. Setting default *goto => %s', self.possible_goto)
            entity['goto'] = self.possible_goto

        desc_buffer = []
        multiline_param_name = None
        multiline_param_value = []

        for idx, line in enumerate(lines):
            line = line.rstrip('\n')
            logging.debug('%s: %s', idx, line)
            token, params = self.get_inline_tokens(line)
            logging.debug('Token: %s, Params: %s', token, params)

            if token in self.SECTION_PARAM_TOKENS:
                # Finish and save multiline param
                if multiline_param_name:
                    logging.debug('Saving multiline param:\n%s', multiline_param_value)
                    # Save only if there is line with content
                    if any(l.strip('\n ') for l in multiline_param_value):
                        entity[multiline_param_name] = self.parse_param(
                            multiline_param_value,
                            multiline_param_name
                        )

                    multiline_param_name = None
                    multiline_param_value.clear()

                    # In case that param token serves only for closing multiline block
                    if not params:
                        continue

                # Just random string with *something... Consider it to be an desc line
                if not params:
                    logging.debug('...and no multiline parameter. Buffer as description')
                    desc_buffer.append(line)
                    continue

                # Read and save found param
                param_name = params[0].lower()
                param_value = params[1] if len(params) > 1 else ''

                # Check if param is allowed, otherwise consider line as description line
                if param_name not in entity_cls.params:
                    logging.debug('Unsupported parameter [%s]', param_name)
                    desc_buffer.append(line)
                    continue

                if token == Tokens.PARAM:
                    entity[param_name] = self.parse_param(param_value, param_name)
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
                    entity['desc'].append(
                        self.parse_param(desc_buffer.copy(), 'desc')
                    )
                    desc_buffer.clear()

            elif token == Tokens.DESCRIPTION:
                # Collect description lines into buffer
                desc_buffer.append(line)
                logging.debug('Buffer: %s', desc_buffer)

            else:
                continue

        # Finalize multiline data gathering
        if multiline_param_name:
            entity[multiline_param_name] = self.parse_param(
                multiline_param_value,
                multiline_param_name
            )
        if desc_buffer:
            entity['desc'].append(
                self.parse_param(desc_buffer.copy(), 'desc')
            )

        multiline_param_value.clear()
        desc_buffer.clear()

        logging.debug('Entity:\n%s', entity)
        logging.debug('Exporting entity class: %s', entity_cls)

        exported = entity_cls.to_string(entity)
        logging.debug(exported)
        return exported

    def parse_section_params(self, entity_cls, params: list):
        '''Parses section params into type specific list of params for Entity.get() function'''

        # Name param
        # --- forcing TEXT type to avoid malformation in case
        #     action will reuse scene name from parent scene
        section_params = [
            JSPGParam(params[0], ParamTypes.TEXT)
        ]

        if len(params) == 1:
            return section_params

        # Type + optional portrait params
        entity_type_subparams = [p.strip() for p in params[1].split(' ', 1)]
        entity_type = entity_type_subparams[0] if entity_type_subparams[0] else None

        # --- Replace type shortcut with full name and validate type
        entity_type_token = TypeTokens.match(entity_type)
        if entity_type_token:
            entity_type = entity_type_token.name.lower()
        else:
            if entity_type and not entity_type.upper() in TypeTokens.__members__.keys():
                raise ValueError(
                    'Invalid entity\'s type parameter. '
                    '"%s" is not allowed! Use one of: %s' % (
                        entity_type,
                        TypeTokens.__members__.keys()
                    ))

        section_params.append(
            self.parse_param(value=entity_type, param_name='type')
        )

        # --- Check for portrait param or append None
        portrait_param = (self.parse_param(value=entity_type_subparams[1], param_name='portrait')
                          if len(entity_type_subparams) > 1 else
                          None)

        if (entity_type
            and entity_type.upper() in (TypeTokens.DIALOG_LEFT.name, TypeTokens.DIALOG_RIGHT.name)
            and not portrait_param):
            raise ValueError('Portrait is required for Dialog type entity!')

        section_params.append(portrait_param)

        # Entity specific params
        if entity_cls == JSPGAction:
            # Action -> Tag
            section_params.append(
                self.parse_param(value=params[2], param_name='tag')
                if len(params) == 3
                else None
            )

        return section_params

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

    def parse_param(self, value, param_name: str = None) -> JSPGParam:
        '''Assign ParamType to given param, depending of it's format'''
        if not value:
            return None

        logging.debug('Parsing param: %s = %s', param_name, value)

        param_type = None
        param_value = None

        if param_name == 'desc':
            logging.debug("Description buffer")
            lines_count = len([l for l in value if l])
            if lines_count == 1:
                param_type = ParamTypes.QUOTED_TEXT
                param_value = self.wrap_description_line(value[0])
            elif lines_count > 1:
                param_type = ParamTypes.MULTILINE_TEXT
                param_value = self.wrap_multiline_description(value)
            else:
                return None

            logging.debug('Description value (type: %s):\n%s', type(value), value)

            return JSPGParam(type=param_type, value=param_value)

        if isinstance(value, list):
            logging.debug("Multiline param")
            # Multiline case
            if not param_name:
                raise ValueError("Method called for unnamed multiline param! Value: %s" % value)

            if param_name in self.MULTILINE_CODE_PARAMS:
                param_type = ParamTypes.MULTILINE_FUNCTION
                param_value = self.wrap_multiline_function(value)
        else:
            logging.debug("Inline param")
            # Single line case
            if value.startswith("`") and value.endswith("`"):
                param_type = ParamTypes.VARIABLE
                param_value = value[1:-1]
            elif value.startswith("{") and value.endswith("}"):
                param_type = ParamTypes.FUNCTION
                param_value = '()=>%s' % value
            elif value.startswith("(") and value.endswith(")"):
                param_type = ParamTypes.OBJECT
                param_value = '{%s}' % value[1:-1]
            else:
                param_type = ParamTypes.TEXT
                param_value = self.escape_quotes(value)

        logging.debug("Creating JSPGParam: type=%s, value=%s", param_type, param_value)
        if not param_type:
            raise ValueError('Param type is not recognized!')

        return JSPGParam(type=param_type, value=param_value)

    def wrap_multiline_function(self, lines):
        '''Wraps multiline code lines into JS arrow function syntax'''
        return [
            '()=>{',
            *('\n'.join(lines).strip('\n').split('\n')),
            '}'
        ]

    def wrap_description_line(self, line):
        '''Checks for interpolation syntax and wraps line with ``
           to mark line as interpolation-required for JSPG'''
        if not line:
            return

        if self.JS_INTERPOLATION_PATTERN.search(line):
            logging.debug('JS interpolation found. Going to wrap line with `.')
            line = '`%s`' % line
        return '"%s"' % self.escape_quotes(line)

    def wrap_multiline_description(self, buffer):
        '''Checks for interpolation syntax inside multilple lines
           and wraps whole block with `>>> ... ` to mark multiline
           as interpolation-required for JSPG or with `` to make it
           native JavaScript multiline string'''
        if not buffer:
            return

        lines = [
            (
                self.JS_INTERPOLATION_PATTERN.sub(r'\\\1', line)
                if self.JS_INTERPOLATION_PATTERN.search(line) else
                line
            ) for line in buffer
        ]

        lines_changed = lines == buffer
        logging.debug('Lines unchanged?: %s', lines_changed)
        lines[0] = '%s%s' % ('`' if lines_changed else '`>>> ', lines[0])
        lines[:] = ["%s<br>" % line for line in lines]
        lines[-1] = '%s`' % lines[-1]

        return lines

    def escape_quotes(self, line):
        return line.replace('"', r'\"').replace('`', r'\`')


# Instruction processor functions
def jspg_parse_function(lines: list, header: str) -> list:
    '''Converts given JSPG lines into valid JS data'''
    return JSPGParser((header, *lines)).parse()

def js_fake_named_parameters_commenter(lines: list, _):
    '''Searchs and comments fakked named params in given lines'''
    pattern = re.compile(r'\*([a-zA-Z0-9_]+)=', re.MULTILINE)
    replace_by = r'/*\1*/ '
    lines[:] = [pattern.sub(replace_by, line) for line in lines]

    return lines

def jspg_replace_function(lines: list, *replace_options):
    '''Find and replace given pairs'''
    for idx, line in enumerate(lines):
        for option in replace_options:
            find = option[0]
            replace = option[1] if len(option) > 0 else ''
            line = line.replace(find, replace)
        lines[idx] = line

    return lines

def jspg_obsidian_markdown_function(lines: list, _) -> list:
    pattern_action_md = re.compile(r'>\s*\[!.*\]\s*')
    pattern_goto_link = re.compile(r'(\*goto:\s*)\[\[.*#(.*)\]\]')
    pattern_code = re.compile(r'`(\$\{.*\})`')
    for idx, line in enumerate(lines):
        if line.startswith('>') and not line.startswith('>|'):
            # Remove Obsidians block code '>[!...]' for marked actions
            search_result = pattern_action_md.search(line)
            line = ('@ %s' % line.removeprefix(search_result.group(0))
                    if search_result else
                    line.lstrip('> '))

        if line.startswith('*') and line.endswith('*') and len(line.split(':')) > 1:
            # Removes possible italic styling of parameter
            line = line.rstrip('*')

        if line.startswith('*goto:'):
            # Replace link to note's header with header name
            search_result = pattern_goto_link.search(line)
            if search_result and search_result.group(2):
                goto_link = search_result.group(2).split()[0]
                line = '%s%s' % (search_result.group(1), goto_link)

        # Remove code wrapping
        line = pattern_code.sub(r'\1', line)

        lines[idx] = line

    return lines

class JSPGProcessor(ProcessorInterface):
    '''Provide access to JSPG processors'''
    processors = {
        '$js_fake_named_params': {
            'processor': js_fake_named_parameters_commenter
        },
        '$replace': {
            'processor': jspg_replace_function,
            'separator': ':',
            'stackable': True,
            'min_params': 1
        },
        '#obsidian_md': {
            'processor': jspg_obsidian_markdown_function
        },
        Tokens.SCENE.value: {
            'processor': jspg_parse_function
        },
        Tokens.ACTION.value: {
            'processor': jspg_parse_function
        }
    }

    # instructions = []

    def __init__(self):
        self.instructions = []

    def check_for_instruction(self, line: str) -> bool:
        line = line.strip()

        for token, properties in JSPGProcessor.processors.items():
            if not line.startswith(token):
                continue

            processor_data = {
                "function": properties['processor'],
                "token": token,
                "params": [],
            }

            params = []
            sep = properties.get('separator')
            if sep:
                line = line.replace(r'\%s' % sep, '~{%s}' % ord(sep))
                instruction_parts = line.split(sep)
                # Extra check for token matching
                if instruction_parts[0].strip() != token:
                    return False
                params = [p.strip().replace('~{%s}' % ord(sep), sep) for p in instruction_parts[1:]]
            else:
                params = [line]

            # Check for minimum of prarams found or all are empty
            # if not - skip instruction
            if not (len(params) >= properties.get('min_params', 0)) or not any(params):
                return False

            # For stackable instructions - find existing one and update with new params
            if properties.get('stackable'):
                for instr in self.instructions:
                    if instr.get('token') == '$replace':
                        instr.get('params').append(params)
                        return True

                # If new - save params as list:
                params = [params]

            processor_data['params'] = params

            self.instructions.append(processor_data)
            return True

        return False

    def has_instructions(self) -> bool:
        logging.debug('Instructions count: %s\n%s', len(self.instructions), self.instructions)
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
    return JSPGProcessor
