# ezbld
Small tool for files composition.

# How To
1. Copy `ezbld` to any directory
1. Set up artifacts build configurations (e.g. `artifacts.ini`):
    - Each artifact should have separate section, where section name is name of the resulting artifact (e.g. for section `[myscipt.js]` artifact will be  `myscript.js`)
    - `order` defines list of relative paths to files to compose
1. Set up settings file (e.g. `settings.ini`):
    - `Paths -> projectPath` - absolute path to your project
    - `Paths -> buildTo` - relative path to put debug builds
    - `Files -> config` - relative path of artifacts build configuration
1. Run `py ezbld.py -s path_to_settings_file` (e.g. `py ezbld.py -s settings.ini`)

# Overview
- [Settings file (settings.ini)](#settings)
- [Artifacts build config (artifacts.ini)](#artifact)
- [Processors](#processors)
    - [Custom processor](#processors.custom)
    - [JavaScript processor](#processors.js)
    - [JSPG processor](#processors.jspg)


Tool helps compose group of files into single file keeping given order of content. Files may also be processed by custom processor before merging.

## Settings file (settings.ini) <a name='settings'></a>

`.INI` file that contains settings for ezbld script and should be passed as `-s` parameter to script on launch.

File content:
- `[General] -> release = (yes/no)` -- defines build mode. On `release=yes` artifact will be written at `Paths.projectPath/Paths.releaseTo` directory. Otherwise target location will be `Paths.projectPath/Paths.buildTo` and artifact filename will contain build version (e.g. `artifact.js-0.0.1.1`).
- `[Version]` section -- defined artifact version. Build version will be added in non-release build sequence. Build version number will be picked from `Files.versionTracker` file at the `Paths.projectPath` directory.
- `[Paths] -> projectPath` -- absolute path to project. Other paths will be calculated relatively to this path.
- `[Paths] -> defaultSourceDir` -- relative path that will be used to calculate artifacts source files location.
- `[Paths] -> buildTo` -- relative path of target location for non-release artifacts.
- `[Paths] -> releaseTo` -- relative path of target location for release artifacts.
- `[Files] -> config` -- relative path for artifacts build configuration `.INI` file.
- `[Files] -> versionTracker` -- name of the file for build version tracking.
- `[Processors]` -- section contains list of files processors to load, in format `processorName = packageName.moduleName`

## Artifacts build config (artifacts.ini) <a name='artifact'></a>
`.INI` file that contains build configuration for each artifact. File name should be declared in `Settings file -> [Files] -> config`.

File content:
- `[ArtifactName]` section -- defines one specific artifact to be build, where:
    - `processor` -- name of the processor to apply to source files.
    - `source_dir` -- overwrites `Paths.defaultSourceDir` and sets relative path of artifact's source files.
    - `target_dir` -- relative path of artifact target location (added to `Paths.buildTo/releaseTo` path).
    - `header_message` -- optional text message to be added in the very beginning of the build artifact. Placeholders `{version}` and `{timestamp}` will be replaced with actual build data using `.format()` function.
    - `order` -- ordered list of files and instructions to use as sources, each file/instuction at separate line:
        - File paths relative to source directory (`Paths.defaultSourceDir` or `source_dir`, if defined).
        - All files in the directory or masked by extenstion (e.g. `path/to/*` or `path/to/*.js` or multiple extensions `path/to/*.txt|md`). This will not include files in nested directories!
        - Files content will be added to artifact directly or after processing, if processor instructions are given in files.
        - Lines in format `>>'Text in single quotes'` will be directly added to artifact.

## Processors <a name='processors'></a>
File content may be modified before addition by text processor specified in the artifacts build config. To mark file as processible - add an processor instruction line in the beggining of the file and specify `processor` parameter at artifact build config with the name from `Processors` section of settings file.

### Custom processors  <a name='processors.custom'></a>
To add custom processor one need to:
- create new `.py` file
    - import `from ezbld import ProcessorInterface`
    - inherit a class from `ProcessorInterface` and implement methods:
        - `check_for_instruction(self, line: str) -> bool` - checks passed line for processor's instruction, save instruction in processor's pool and return True if valid instruction found, or False if not.
		- `has_instructions(self) -> bool` - returns True if there is any instruction saved in the processor's internal instuctions pool.
		- `process(self, content: list) -> list` - processes given lines according to processor's internal instructions pool.
    - implement separate function `get() -> ProcessorInterface` which returns processor class

To use custom processor:
- add processor to settings file (`settings.ini`) to `[Processors]` section under unique name and value in format `package.modulename` (e.g. `processors\js.py` -> `processors.js`)
- set `processor` property for artifact in artifacts build config (e.g. `artifacts.ini`)


### JavaScript processor <a name='processors.js'></a>

Processor to wrap JS code into closures/functions or mappings.

##### Instruction prefix:
`//@`
##### Instructions
- `wrap`
- `map`

#### `wrap` instruction params:
Wrap instruction wraps file content in specific JS structure and adds needed indent to each line.
##### Param1 - Wrap Type:
One of following `object`, `function`, `closure`. Type of wrapping:
- for `object` content will be wrapped in `Param2 = {...}`,
- `function` - `Param2 = function (Param3) {...}`,
- `closure` - `Param2 = new (function (Param3){})`

##### Param2 - Name
Name of the resulting object.

##### Param3 - Function parameters
Comma-separated list of function parameters. May include defaults values. E.g. `name, type, size=5`

##### Examples
Source file:
```js
//@wrap:function:MyFunction:name, size=5
console.log(name)
size = size + 2
console.log(size)
```
After processor:
```js
MyFunction = function (name, size=5) {
    console.log(name)
    size = size + 2
    console.log(size)
}
```

#### `map` instruction params:
Maps keys and values in the object. File should be formatted as list of `key = value`, each pair on separate line. Value may be set to `*` - processor will replace it with name of the key (e.g. for mapping 2 objects with similar keys).

##### Param1 - Object name
Name of the resulting object

##### Param2 - Keys source object
Optional, name of object that contains keys

##### Param3 - Values source object
Optional, name of object that contains values

##### Examples:
```js
1) //@map:MapName::
   'A' = 1
   'B' = 2
   ----processed to----
   MapName['A'] = 1;
   MapName['B'] = 2;

2) //@map:MapName:Source:Target
   KeyA = Foo
   KeyB = Bar
   ----processed to----
   MapName[Source.KeyA] = Target.Foo;
   MapName[Source.KeyB] = Target.Bar;

3) //@map:MapName:Source:
   KeyA = 123
   KeyB = 456
   ----processed to----
   MapName[Source.KeyA] = 123;
   MapName[Source.KeyB] = 456;

4) //@map:MapName::Target
   'A' = Foo
   'B' = Bar
   ----processed to----
   MapName['A'] = Target.Foo;
   MapName['B'] = Target.Bar;+
```


### JSPG processor<a href='#processors.jspg'></a>
Converts JSPG markup files to native JS. 

##### Instructions
- `# `
- `@ `
- `#obsidian_md`
- `$js_fake_named_params`
- `$replace`

#### `# ` (Scene) instruction:
Defines start of the JSPG Scene. Takes up to 2 parameters separated by `|`
```
# NameOfTheScene | Type Portrait
```

##### Param1 - Scene name
Name of the scene

##### Param2 - Scene type and portrait
Whitespace separated type and portrait parameters. 

#### `@ ` (Action) instruction:
Defines start of the JSPG Action. Takes up to 3 parameters separated by `|`

```
# NameOfTheScene | Type Portrait | Tag
```

##### Param1 - Action name
Name of the scene

##### Action - Scene type and portrait
Whitespace separated type and portrait parameters. 

##### Param3 - Tag name
Tag name of the action.

#### `#obsidian_md` instruction:
Marks file as created using Obsidian markdown syntax. Takes no parameters.

Applies next changes to file content:
a) removes block syntax (`>`) and converts Obsidian block's header to JSPG action section:
```
>[!@] Action name | Type Portrait | Tag
>*param: value

to
@ Action name | Type Portrait | Tag
*param: value
```
b) converts markdown link to section `*goto: [[Note#Section]]` in to JSPG-compatible link `*goto: Section`

c) removes markdown italic wrapping in parameter-like lines (e.g. `*goto: Name*` will become `*goto: Name`)

#### `$js_fake_named_params` instruction:
Same as JS processor. Comments parameter names:
`$h.Img(src=MyPic.jpg)` will become valid JS `$h.Img(/*src=*/MyPic.jpg`

#### `$replace` instruction:
Scans and replace given substrings using `.replace` method. Takes up to 2 parameters separated by `:`.
```
$replace:AAA:BBB
$replace:    SOMETHING   : WITH ANOTHER THING
```
Replacement parameters will be trimmed.

Several replace instructions will be stacked and applied in given order by one passthrough.

##### Param1 - Target
Target substring to replace.

##### Param2 - Replacement (optional)
Substring to insert. If not defined - target substring will be removed.
