try:
    import numpy
except ImportError: # pragma: no cover
    numpy = None

from vistrails.core.modules.config import ModuleSettings
from vistrails.core.modules.vistrails_module import Module, ModuleError


class InternalModuleError(Exception):
    """Track ModuleError in subclasses."""

    def raise_module_error(self, module_obj):
        raise ModuleError(module_obj, self.message)


class TableObject(object):
    columns = None # the number of columns in the table
    rows = None # the number of rows in the table
    names = None # the names of the columns
    name = None # a name for the table (useful for joins, etc.)

    def get_column(self, i, numeric=False): # pragma: no cover
        """Gets a column from the table as a list or numpy array.

        If numeric=False (the default), the data is returned 'as-is'. It might
        either be bytes (=str), unicode or number (int, long, float).

        If numeric=True, the data is returned as a numpy array if numpy is
        available, or as a list of floats.
        """
        raise NotImplementedError


class Table(Module):
    _input_ports = [('name', '(org.vistrails.vistrails.basic:String)')]
    _output_ports = [('value', 'Table')]

    def set_output(self, port_name, value):
        if value is not None and port_name == 'value':
            if value.name is None:
                value.name = self.force_get_input('name', None)
        Module.set_output(self, port_name, value)


def choose_column(column_names=None, name=None, index=None):
    """Selects a column in a table either by name or index.

    If both are specified, the function will make sure that they represent the
    same column.
    """
    if name is not None:
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        if column_names is None:
            raise ValueError("Unable to get column by name: table doesn't "
                             "have column names")
        try:
            name_index = column_names.index(name)
        except ValueError:
            try:
                name_index = column_names.index(name.strip())
            except ValueError:
                raise ValueError("Column name was not found: %r" % name)
        if index is not None:
            if name_index != index:
                raise ValueError("Both a column name and index were "
                                 "specified, and they don't agree")
        return name_index
    elif index is not None:
        return index
    else:
        raise ValueError("No column name nor index specified")


def choose_columns(column_names=None, names=None, indexes=None):
    """Selects a list of columns from a table.

    If both the names and indexes lists are specified, the function will make
    sure that they represent the same list of columns.
    Columns may appear more than once.
    """
    if names is not None:
        if column_names is None:
            raise ValueError("Unable to get column by names: table "
                             "doesn't have column names")
        result = []
        for name in names:
            if isinstance(name, unicode):
                name = name.encode('utf-8')
            try:
                idx = column_names.index(name)
            except ValueError:
                try:
                    idx = column_names.index(name.strip())
                except:
                    raise ValueError("Column name was not found: %r" % name)
            indexes.append(idx)
        if indexes is not None:
            if result != indexes:
                raise ValueError("Both column names and indexes were "
                                 "specified, and they don't agree")
        return result
    elif indexes is not None:
        return indexes
    else:
        raise ValueError("No column names nor indexes specified")


class ExtractColumn(Module):
    """Gets a single column from a table, as a list.

    Specifying one of 'column_name' or 'column_index' is sufficient; if you
    provide both, the module will check that the column has the expected name.
    """
    _input_ports = [
            ('table', Table),
            ('column_name', '(org.vistrails.vistrails.basic:String)',
             {'optional': True}),
            ('column_index', '(org.vistrails.vistrails.basic:Integer)',
             {'optional': True}),
            ('numeric', '(org.vistrails.vistrails.basic:Boolean)',
             {'optional': True, 'defaults': "['False']"})]
    _output_ports = [
            ('value', '(org.vistrails.vistrails.basic:List)')]

    def compute(self):
        table = self.get_input('table')
        try:
            column_idx = choose_column(
                    column_names=table.names,
                    name=self.force_get_input('column_name', None),
                    index=self.force_get_input('column_index', None))
        except ValueError, e:
            raise ModuleError(self, e.message)

        self.set_output('value', table.get_column(
                column_idx,
                self.get_input('numeric', allow_default=True)))


class BuiltTable(TableObject):
    def __init__(self, columns, nb_rows, names):
        self.columns = len(columns)
        self.rows = nb_rows
        self.names = names

        self._columns = columns

    def get_column(self, i, numeric=False):
        if numeric and numpy is not None:
            return numpy.array(self._columns[i], dtype=numpy.float32)
        else:
            return self._columns[i]


class BuildTable(Module):
    """Builds a table by putting together columns from multiple sources.

    Input can be a mix of lists, which will be used as single columns, and
    whole tables, whose column names will be mangled.
    """
    _settings = ModuleSettings(configure_widget=
            'vistrails.packages.tabledata.widgets:BuildTableWidget')
    _output_ports = [('value', Table)]

    def __init__(self):
        Module.__init__(self)
        self.input_ports_order = []

    def compute(self):
        items = None
        if self.input_ports_order: # pragma: no branch
            items = [(p, self.get_input(p))
                     for p in self.input_ports_order]
        if not items:
            raise ModuleError(self, "No inputs were provided")

        nb_rows = None
        cols = []
        names = []
        for portname, item in items:
            if isinstance(item, TableObject):
                if nb_rows is not None:
                    if item.rows != nb_rows:
                        raise ModuleError(
                                self,
                                "Different row counts: %d != %d" % (
                                item.rows, nb_rows))
                else:
                    nb_rows = item.rows
                cols.extend(item.get_column(c)
                            for c in xrange(item.columns))
                if item.names is not None:
                    names.extend(item.names)
                else:
                    names.extend("%s col %d" % (portname, i)
                                 for i in xrange(len(cols) - len(names)))
            else:
                if nb_rows is not None:
                    if len(item) != nb_rows:
                        raise ModuleError(
                                self,
                                "Different row counts: %d != %d" % (
                                len(item), nb_rows))
                else:
                    nb_rows = len(item)
                cols.append(item)
                names.append(portname)

        self.set_output('value', BuiltTable(cols, nb_rows, names))


_modules = [(Table, {'abstract': True}), ExtractColumn, BuildTable]
