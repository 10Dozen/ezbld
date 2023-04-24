# ezbld
Small tool for files composition.

# How To
1. Copy `ezbld` to any directory
1. Set up artifacts build configurations (e.g. `example_project/artifacts.ini`):
    - Each artifact should have separate section, where section name is the name of the resulting artifact file (e.g. for section `[myscipt.js]` artifact will be  `myscript.js`)
    - `order` defines list of relative paths to files to compose
1. Set up settings file (e.g. `settings.ini`):
    - `Paths -> projectPath` - absolute path of your project
    - `Paths -> buildTo` - relative path to put debug builds
    - `Files -> config` - relative path of artifacts build configuration
1. Run `py ezbld.py -s path_to_settings_file` (e.g. `py ezbld.py -s settings.ini`)

# Overview
- [Settings file (settings.ini)](#settings)
- [Artifacts build config (artifacts.ini)](#artifact)
- [Processors](#processors)
    - [JavaScript processor](#processors.js)
    - [Custom processor](#processors.custom)


Tool helps compose group of files into a single file keeping given order of content. Files may also be processed by custom processor before merging.

## Settings file (settings.ini) <a name='settings'></a>

`.INI` file that contains settings for ezbld script and should be passed as `-s` parameter to script on launch.

File content:
- `[General] -> release = (yes/no)` -- defines build mode. On `release=yes` artifact will be written at `Paths.projectPath/Paths.releaseTo` directory. Otherwise target location will be `Paths.projectPath/Paths.buildTo` and artifact filename will contain build version (e.g. `artifact.js-0.0.1.1`).
- `[Version]` section -- defines artifact version. Last digit (build version) will be picked from `Files.versionTracker` file at the `Paths.projectPath` directory (or `0` if there is no file).
- `[Paths] -> projectPath` -- absolute path to project. Other paths will be calculated relatively to this path.
- `[Paths] -> defaultSourceDir` -- relative path that will be used to calculate artifacts source files location.
- `[Paths] -> buildTo` -- relative path of target location for non-release artifacts.
- `[Paths] -> releaseTo` -- relative path of target location for release artifacts.
- `[Files] -> config` -- relative path for artifacts build configuration `.INI` file.
- `[Files] -> versionTracker` -- name of the file for build version tracking. File created/overwritten on each successfull build.
- `[Processors]` -- section contains list of files processors to load, in format `processorName = packageName.moduleName`

## Artifacts build config (artifacts.ini) <a name='artifact'></a>
`.INI` file that contains build configuration for each artifact. File name should be declared in `Settings file -> [Files] -> config`.

File content:
- `[ArtifactName]` section -- defines one specific artifact to be build, where:
    - `processor` -- name of the processor to apply to source files.
    - `source_dir` -- overwrites `Paths.defaultSourceDir` and sets relative path of artifact's source files.
    - `target_dir` -- relative path of artifact target location (added to `Paths.buildTo/releaseTo` path).
    - `order` -- ordered list of files and instructions to use as sources, each file/instuction at separate line:
        - File paths relative to source directory (`Paths.defaultSourceDir` or `source_dir`, if defined).
        - Files content will be added to artifact directly or after processing, if processor instructions are given in files.
        - For lines in format `>>'Text in single quotes'` text in quotes will be directly added to artifact.

## Processors <a name='processors'></a>
File content may be modified before addition by text processor specified in the artifacts build config. To mark file as processible - add an processor instruction line in the beggining of the file and specify `processor` parameter at artifact build config with name from `Processors` section of settings file.

Instruction format depends on processor used.

### JavaScript processor <a name='processors.js'></a>
##### Instruction prefix: 
`//@`

##### Instruction Format
`//@Instruction:Param1:Param2:...:ParamN`

where,
- `Instruction` -- name of the instruction to apply to file.
- `ParamN` -- parameters of instruction

To skip param place `:` right after previous `:` symbol (e.g. `prefixInstuction::param`)

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


### Custom processors  <a name='processors.custom'></a>
To add custom processor one need to:
- create new `.py` file
    - import `from ezbld import ProcessorInterface`
    - inherit a class from `ProcessorInterface` and implement methods:
        - `get_definitions()` should return list of supported instructions (with prefix) to search in source file (e.g. prefix is `#` and supported instuctions are (`add_indent`, `remove_indent`), then function should return list `['#add_indent', '#remove_indent']`)
        - `get_processor(instruction: str)` should return processor function based on given instruction line found in source file
    - create a processor function(s) with `func(lines: list) -> list` signature, where `lines` is a list of lines of the source file (except instuction line). Function must return list of processed lines
    - implement function `get() -> ProcessorInterface` which returns processor class

To use custom processor:
- add processor to settings file (`settings.ini`) to `[Processors]` section under unique name and value in format `package.modulename` (e.g. `processors\js.py` -> `processors.js`)
- set `processor` property for artifact in artifacts build config (e.g. `artifacts.ini`)
    