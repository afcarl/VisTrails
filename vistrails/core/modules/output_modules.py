import copy
import os
import sys
import unittest

from vistrails.core.configuration import ConfigurationObject, ConfigField, ConfigPath, get_vistrails_persistent_configuration, get_vistrails_temp_configuration
from vistrails.core.modules.vistrails_module import Module, NotCacheable, ModuleError
from vistrails.core.modules.config import IPort, OPort
import vistrails.core.system

class OutputMode(object):
    mode_type = None
    priority = -1

    @classmethod
    def can_compute(cls):
        return False

    def compute_output(self, output_module, configuration=None):
        raise NotImplementedError("Subclass of OutputMode should implement "
                                  "this")

# Ideally, these are globally and locally configurable so that we use
# global settings if nothing is set locally (e.g. output directory)
class OutputModeConfig(dict):
    mode_type = None
    _fields = []
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        for k, v in self.iteritems():
            if not self.has_field(k):
                raise ValueError('Field "%s" is not declared for class "%s"' %
                                 (k, self.__class__.__name__))

    @classmethod
    def has_field(cls, k):
        def cls_has_field(c):
            if hasattr(c, '_fields'):
                if not hasattr(c, '_field_dict'):
                    c._field_dict = dict((f.name, f.default_val) 
                                       for f in c._fields)
                if k in c._field_dict:
                    return True
            return False
        return any(cls_has_field(bcls) 
                   for bcls in ([cls,] + list(cls.__bases__)))

    @classmethod
    def get_default(cls, k):
        def cls_get_default(c):
            if hasattr(c, '_fields'):
                if not hasattr(c, '_field_dict'):
                    c._field_dict = dict((f.name, f.default_val) 
                                       for f in c._fields)
                if k in c._field_dict:
                    return c._field_dict[k]
            return None

        for bcls in ([cls,] + list(cls.__bases__)):
            retval = cls_get_default(bcls)
            if retval is not None:
                return retval
        return None

    @classmethod
    def has_from_config(cls, config, k):
        if hasattr(cls, 'mode_type'):
            mode_type = cls.mode_type
            if config.has(mode_type):
                subconfig = getattr(config, mode_type)
                if subconfig.has(k):
                    return True
        return False

    @classmethod
    def get_from_config(cls, config, k):
        if hasattr(cls, 'mode_type'):
            mode_type = cls.mode_type
            if config.has(mode_type):
                subconfig = getattr(config, mode_type)
                if subconfig.has(k):
                    return getattr(subconfig, k)
        return None

    @classmethod
    def has_override(cls, k):
        config = get_vistrails_temp_configuration().outputSettings.overrides
        return cls.has_from_config(config, k)

    @classmethod
    def get_override(cls, k):
        config = get_vistrails_temp_configuration().outputSettings.overrides
        return cls.get_from_config(config, k)

    @classmethod
    def has_global_setting(cls, k):
        config = get_vistrails_persistent_configuration().outputSettings
        return cls.has_from_config(config, k)

    @classmethod
    def get_global_setting(cls, k):
        config = get_vistrails_persistent_configuration().outputSettings
        return cls.get_from_config(config, k)

    @classmethod
    def has_config_setting(cls, k):
        return cls.has_override(k) or cls.has_global_setting(k)

    def __setitem__(self, k, v):
        if not self.has_field(k):
            raise ValueError('Setting "%s" is not declared for class "%s"' %
                             (k, self.__class__.__name__))
        dict.__setitem__(self, k, v)

    def __getitem__(self, k):
        if self.has_override(k):
            return self.get_override(k)
        try:
            return dict.__getitem__(self, k)
        except KeyError, e:
            if self.has_global_setting(k):
                return self.get_global_setting(k)
            else:
                if self.has_field(k):
                    return self.get_default(k)
            raise e

    def __hasitem__(self, k):
        return (self.has_field(k) or dict.__hasitem__(self, k) or 
                self.has_override(k) or self.has_global_setting(k))

class OutputModule(NotCacheable, Module):
    _input_ports = [IPort('value', "Variant"),
                    IPort('mode_type', "String"),
                    IPort('configuration', "Dictionary")]

    # configuration is a dictionary of dictionaries where root-level
    # keys are mode_types and the inner dictionaries are
    # workflow-specific settings

    # want to have mode inheritance here...

    @classmethod
    def ensure_mode_dict(cls):
        if not hasattr(cls, '_output_modes_dict'):
            if hasattr(cls, '_output_modes'):
                cls._output_modes_dict = \
                                dict((mcls.mode_type, (mcls, mcls.priority))
                                     for mcls in cls._output_modes)
            else:
                cls._output_modes_dict = {}
            
    @classmethod
    def register_output_mode(cls, mode_cls, priority=None):
        if mode_cls.mode_type is None:
            raise ValueError("mode_cls.mode_type must not be None")
        if priority is None:
            priority = mode_cls.priority
        cls.ensure_mode_dict()
        if not hasattr(cls, '_output_modes'):
            cls._output_modes = []
        cls._output_modes.append(mode_cls)
        cls._output_modes_dict[mode_cls.mode_type] = (mode_cls, priority)

    @classmethod
    def set_mode_priority(cls, mode_type, priority):
        cls.ensure_mode_dict()

        if mode_type not in cls._output_modes_dict:
            raise ValueError('mode_type "%s" is not set for this module' % 
                             mode_type)
        cls._output_modes_dict[mode_type][1] = priority

    def compute(self):
        mode_cls = None
        self.ensure_mode_dict()
        if self.has_input("mode_type"):
            # use user-specified mode_type
            mode_type = self.get_input("mode_type")
            if mode_type not in self._output_modes_dict:
                raise ModuleError(self, 'Cannot output in mode "%s" because '
                                  'that mode has not been defined' % mode_type)
            mode_cls = self._output_modes_dict[mode_type][0]
        else:
            # FIXME should have user-setable priorities!

            # determine mode_type based on registered modes by priority,
            # checking if each is possible
            for mcls, _ in sorted(self._output_modes_dict.itervalues(), 
                                       reverse=True,
                                       key=lambda mode_t: mode_t[1]):
                if mcls.can_compute():
                    mode_cls = mcls
                    break

        if mode_cls is None:
            raise ModuleError(self, "No output mode is valid, output cannot "
                              "be generated")

        mode = mode_cls()
        mode_config_cls = mode_cls.config_cls
        mode_config = None
        configuration = self.force_get_input('configuration')
        if configuration is not None:
            for k, v in configuration.iteritems():
                if k == mode.mode_type:
                    mode_config = mode_config_cls(v)
                    break

        self.annotate({"output_mode": mode.mode_type})        
        mode.compute_output(self, mode_config)
                
class StdoutModeConfig(OutputModeConfig):
    mode_type = "stdout"
    _fields = []

class StdoutMode(OutputMode):
    mode_type = "stdout"
    priority = 2
    config_cls = StdoutModeConfig

    @classmethod
    def can_compute(cls):
        return True

class FileModeConfig(OutputModeConfig):
    mode_type = "file"
    _fields = [ConfigField('file', None, ConfigPath),
               ConfigField('basename', None, str),
               ConfigField('prefix', None, str),
               ConfigField('suffix', None, str),
               ConfigField('dir', None, ConfigPath),
               ConfigField('series', False, bool),
               ConfigField('overwrite', False, bool),
               ConfigField('seriesPadding', 3, int),
               ConfigField('seriesStart', 0, int)]

class FileMode(OutputMode):
    mode_type = "file"
    priority = 1
    config_cls = FileModeConfig
    
    # need to reset this after each execution!
    series_next = 0

    @classmethod
    def can_compute(cls):
        return True

    def get_series_num(self):
        retval = FileMode.series_next 
        FileMode.series_next += 1
        return retval

    def get_filename(self, configuration, full_path=None, filename=None,
                     dirname=None, basename=None, prefix=None, suffix=None,
                     overwrite=None, series=False, series_padding=3):
        # if prefix/suffix/series are overridden, want to use them
        # instead of name...
        if full_path is None and configuration is not None:
            # use file if overridden or none of the file params are
            # overridden and the file is not None

            overwrite = configuration['overwrite']
            if (configuration.has_override('file') or
                (not (configuration.has_override('basename') or
                      configuration.has_override('prefix') or
                      configuration.has_override('suffix') or
                      configuration.has_override('dir') or
                      configuration.has_override('series') or
                      configuration.has_override('seriesPadding') or
                      configuration.has_override('seriesStart')) and
                 'file' in configuration and
                 configuration['file'] is not None)):
                full_path = configuration['file']
            else:
                basename = configuration['basename']
                prefix = configuration['prefix']
                suffix = configuration['suffix']
                dirname = configuration['dir']
                series = configuration['series']
                series_padding = configuration['seriesPadding']

        if full_path is None:                
            # should any of these necessitate series=True?
            if basename is None:
                basename = 'vt_out'
            if prefix is None:
                prefix = ''
            if suffix is None:
                suffix = ''
            if dirname is None:
                # FIXME should unify with VisTrails output
                # directory global!  should check for abspath (if
                # not, use relative to global output directory)
                dirname = ''

            # seriesPadding and series have defaults so no
            # need to default them

            if not overwrite and series:
                # need to find first open slot
                full_path = None
                while full_path is None or os.path.exists(full_path):
                    series_str = (("%%0%dd" % series_padding) % 
                                  self.get_series_num())
                    full_path = os.path.join(dirname, "%s%s%s%s" % 
                                             (prefix, basename, 
                                              series_str, suffix))
            else:
                if series:
                    series_str = (("%%0%dd" % series_padding) % 
                                  self.get_series_num())
                else:
                    series_str = ""
                full_path = os.path.join(dirname, "%s%s%s%s" % 
                                         (prefix, basename, series_str, 
                                          suffix))
            if not overwrite and os.path.exists(full_path):
                raise IOError('File "%s" exists and overwrite is False' % full_path)

        print "GET FILENAME RETURNING:", full_path
        return full_path
        
class FileToFileMode(FileMode):
    def compute_output(self, output_module, configuration=None):
        old_fname = output_module.get_input('value').name
        full_path = self.get_filename(configuration)
        # we know we are in overwrite mode because it would have been
        # flagged otherwise
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except OSError, e:
                raise ModuleError(output_module, 
                                  ('Could not delete existing '
                                   'path "%s"' % full_path))
        try:
            vistrails.core.system.link_or_copy(old_fname, full_path)
        except OSError, e:
            msg = "Could not create file '%s': %s" % (full_path, e)
            raise ModuleError(output_module, msg)

class FileToStdoutMode(StdoutMode):
    def compute_output(self, output_module, configuration=None):
        fname = output_module.get_input('value').name
        with open(fname, 'r') as f:
            for line in f:
                sys.stdout.write(line)

class SpreadsheetModeConfig(OutputModeConfig):
    _input_ports = [IPort('row', 'Integer'),
                    IPort('col', 'Integer'),
                    IPort('sheet', 'String')]

class SpreadsheetMode(OutputMode):
    mode_type = 'spreadsheet'
    priority = 0
    
    @classmethod
    def can_compute(cls):
        # FIXME check if spreadsheet is enabled
        return True

    def compute_output(self, output_module, configuration=None):
        pass

class GenericToStdoutMode(StdoutMode):
    def compute_output(self, output_module, configuration=None):
        value = output_module.get_input('value')
        print >>sys.stdout, value

class GenericToFileMode(FileMode):
    def compute_output(self, output_module, configuration=None):
        value = output_module.get_input('value')
        filename = self.get_filename(configuration)
        with open(filename, 'w') as f:
            print >>f, value

class GenericOutput(OutputModule):
    _output_modes = [GenericToStdoutMode, GenericToFileMode]

class FileOutput(OutputModule):
    # should set file as a higher priority here...
    _input_ports = [('value', 'File')]
    _output_modes = [FileToStdoutMode, FileToFileMode]

class ImageFileOutput(FileOutput):
    pass

class ImageOutput(OutputModule):
    # need specific spreadsheet image mode here
    pass

class RichTextOutput(OutputModule):
    # need specific spreadsheet richtext mode here
    pass

_modules = [OutputModule, GenericOutput, FileOutput]

# need to put WebOutput, ImageOutput, RichTextOutput, SVGOutput, VTKOutput, MplOutput, etc. elsewhere

class TestOutputModeConfig(unittest.TestCase):
    def test_fields(self):
        class AlteredFileModeConfig(FileModeConfig):
            _fields = [ConfigField("newattr", 3, int)]
            
        self.assertTrue(AlteredFileModeConfig.has_field("overwrite"))
        self.assertTrue(AlteredFileModeConfig.has_field("newattr"))

    def test_config(self):
        config_obj = ConfigurationObject(file=ConfigurationObject(seriesStart=5))
        self.assertTrue(FileModeConfig.has_from_config(config_obj, 
                                                       "seriesStart"))
        self.assertEqual(FileModeConfig.get_from_config(config_obj, 
                                                        "seriesStart"), 5)
        
    def test_subclass_config(self):
        class AlteredFileModeConfig(FileModeConfig):
            mode_type = "file"
            _fields = [ConfigField("newattr", 3, int)]
        config_obj = ConfigurationObject(file=ConfigurationObject(seriesStart=5))
        self.assertEqual(AlteredFileModeConfig.get_from_config(config_obj, 
                                                        "seriesStart"), 5)

    def test_get_item(self):
        config = FileModeConfig()
        self.assertEqual(config["seriesStart"], 0)

if __name__ == '__main__':
    import vistrails.core.application
    app = vistrails.core.application.init()
    unittest.main()
