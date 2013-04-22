import vistrails.core
import vistrails.core.db.action
import vistrails.core.application
import vistrails.db.versions
import vistrails.core.modules.module_registry
import vistrails.core.modules.utils
from vistrails.core.modules.vistrails_module import Module, ModuleError, \
    ModuleConnector, InvalidOutput
from vistrails.core.modules.basic_modules import NotCacheable, Constant
from vistrails.core.vistrail.pipeline import Pipeline
from vistrails.core.vistrail.annotation import Annotation
from vistrails.core.vistrail.group import Group
from vistrails.core.vistrail.module_function import ModuleFunction
from vistrails.core.vistrail.module_param import ModuleParam
from vistrails.core.vistrail.vistrail import Vistrail
from vistrails.core.db.locator import XMLFileLocator
from vistrails.core.vistrail.controller import VistrailController
from vistrails.core.interpreter.default import get_default_interpreter
from vistrails.core.db.io import serialize, unserialize
from vistrails.core.log.module_exec import ModuleExec
from vistrails.core.log.group_exec import GroupExec
from vistrails.core.log.machine import Machine
from vistrails.db.domain import IdScope

import copy
import inspect
from itertools import izip
import os
import tempfile

from IPython.parallel import Client


################################################################################
# This function is sent to the engines which execute it
#
# It receives the workflow, and the list of targeted output ports
#
# It returns the corresponding computed outputs and the execution log
#
def execute_wf(wf, output_ports):
    # Save the workflow in a temporary file
    temp_wf_fd, temp_wf = tempfile.mkstemp()

    f = open(temp_wf, 'w')
    f.write(wf)
    f.close()
    os.close(temp_wf_fd)

    # Clean the cache
    interpreter = get_default_interpreter()
    interpreter.flush()

    # Load the Pipeline from the temporary file
    vistrail = Vistrail()
    locator = XMLFileLocator(temp_wf)
    workflow = locator.load(Pipeline)

    # Build a Vistrail from this single Pipeline
    action_list = []
    for module in workflow.module_list:
        action_list.append(('add', module))
    for connection in workflow.connection_list:
        action_list.append(('add', connection))
    action = vistrails.core.db.action.create_action(action_list)

    vistrail.add_action(action, 0L)
    vistrail.update_id_scope()
    tag = 'parallel flow'
    vistrail.addTag(tag, action.id)

    # Build a controller and execute
    controller = VistrailController()
    controller.set_vistrail(vistrail, None)
    controller.change_selected_version(vistrail.get_version_number(tag))
    execution = controller.execute_current_workflow(
            custom_aliases=None,
            custom_params=None,
            extra_info=None,
            reason='API Pipeline Execution')

    # Build a list of errors
    errors = []
    pipeline = vistrail.getPipeline(tag)
    execution_errors = execution[0][0].errors
    if execution_errors:
        for key in execution_errors:
            module = pipeline.modules[key]
            msg = '%s: %s' %(module.name, execution_errors[key])
            errors.append(msg)

    # Get the execution log from the controller
    module_log = controller.log.workflow_execs[0].item_execs[0]
    machine = controller.log.machine_list[0]
    xml_log = serialize(module_log)
    machine_log = serialize(machine)

    # Get the requested output values
    module_outputs = []
    annotations = module_log.annotations
    for annotation in annotations:
        if annotation.key == 'output':
            module_outputs = annotation.value
            break

    # Store the output values in the order they were requested
    reg = vistrails.core.modules.module_registry.get_module_registry()
    ports = []
    outputs = []
    serializable = []
    for port in output_ports:
        for output in module_outputs:
            if output[0] == port:
                # checking if output port needs to be serialized
                base_classes = inspect.getmro(type(output[1]))
                if Module in base_classes:
                    ports.append(output[0])
                    outputs.append(output[1].serialize())
                    serializable.append(reg.get_descriptor(type(output[1])).sigstring)
                else:
                    ports.append(output[0])
                    outputs.append(output[1])
                    serializable.append(None)
                break

    # Return the dictionary, that will be sent back to the client
    return dict(errors=errors,
                ports=ports,
                outputs=outputs,
                serializable=serializable,
                xml_log=xml_log,
                machine_log=machine_log)

################################################################################
# Map Operator
#
class Map(Module, NotCacheable):
    """The Map Module executes a map operator in parallel on IPython engines.

    The FunctionPort should be connected to the 'self' output of the module you
    want to execute.
    The InputList is the list of values to be scattered on the engines.
    """
    def __init__(self):
        Module.__init__(self)

    def updateUpstream(self):
        """A modified version of the updateUpstream method."""

        # everything is the same except that we don't update anything
        # upstream of FunctionPort
        for port_name, connector_list in self.inputPorts.iteritems():
            if port_name == 'FunctionPort':
                for connector in connector_list:
                    connector.obj.updateUpstream()
            else:
                for connector in connector_list:
                    connector.obj.update()
        for port_name, connectorList in copy.copy(self.inputPorts.items()):
            if port_name != 'FunctionPort':
                for connector in connectorList:
                    if connector.obj.get_output(connector.port) is \
                            InvalidOutput:
                        self.removeInputConnector(port_name, connector)

    def updateFunctionPort(self):
        """
        Function to be used inside the updateUsptream method of the Map module. It
        updates the module connected to the FunctionPort port, executing it in
        parallel.
        """
        nameInput = self.getInputFromPort('InputPort')
        nameOutput = self.getInputFromPort('OutputPort')
        rawInputList = self.getInputFromPort('InputList')

        # Create inputList to always have iterable elements
        # to simplify code
        if len(nameInput) == 1:
            element_is_iter = False
            inputList = [[element] for element in rawInputList]
        else:
            element_is_iter = True
            inputList = rawInputList

        workflows = []
        module = None
        vtType = None

        # iterating through the connectors
        for connector in self.inputPorts.get('FunctionPort'):
            module = connector.obj

            # pipeline
            original_pipeline = connector.obj.moduleInfo['pipeline']

            # module
            module_id = connector.obj.moduleInfo['moduleId']
            vtType = original_pipeline.modules[module_id].vtType

            # serialize the module for each value in the list
            for i, element in enumerate(inputList):
                if element_is_iter:
                    self.element = element
                else:
                    self.element = element[0]

                pipeline_modules = dict((k,m.do_copy()) for k, m in original_pipeline.modules.iteritems())

                # checking type and setting input in the module
                self.typeChecking(connector.obj, nameInput, inputList)
                self.setInputValues(connector.obj, nameInput, element)

                pipeline_db_module = pipeline_modules[module_id]

                # transforming a subworkflow in a group
                # TODO: should we also transform inner subworkflows?
                if pipeline_db_module.is_abstraction():
                    group = Group(id=pipeline_db_module.id,
                                  cache=pipeline_db_module.cache,
                                  location=pipeline_db_module.location,
                                  functions=pipeline_db_module.functions,
                                  annotations=pipeline_db_module.annotations)

                    source_port_specs = pipeline_db_module.sourcePorts()
                    dest_port_specs = pipeline_db_module.destinationPorts()
                    for source_port_spec in source_port_specs:
                        group.add_port_spec(source_port_spec)
                    for dest_port_spec in dest_port_specs:
                        group.add_port_spec(dest_port_spec)

                    group.pipeline = pipeline_db_module.pipeline
                    pipeline_db_module = group

                # getting highest id between functions to guarantee unique ids
                # TODO: can get current IdScope here?
                high_id = 0
                module_functions = pipeline_db_module.functions
                for function in module_functions:
                    if int(function.id) > high_id:
                        high_id = int(function.id)

                # adding function and parameter to module in pipeline
                # TODO: 'pos' should not be always 0 here
                id_scope = IdScope(beginId=long(high_id+1))
                for elementValue, inputPort in izip(element, nameInput):

                    p_spec = pipeline_db_module.get_port_spec(inputPort, 'input')
                    type = p_spec.sigstring[1:-1]

                    mod_function = ModuleFunction(id=id_scope.getNewId(ModuleFunction.vtType),
                                                  pos=0,
                                                  name=inputPort)
                    mod_param = ModuleParam(id=0L,
                                            pos=0,
                                            type=type,
                                            val=elementValue)

                    mod_function.add_parameter(mod_param)
                    pipeline_db_module.add_function(mod_function)

                # store output data
                annotation = Annotation(key='annotate_output', value=True)
                pipeline_db_module.add_annotation(annotation)

                # serializing module
                wf = self.serialize_module(pipeline_db_module)
                workflows.append(wf)

            # getting first connector, ignoring the rest
            break

        # IPython stuff
        try:
            rc = Client()
            engines = rc.ids
            if not engines:
                raise ModuleError(
                        self,
                        "Exception while loading IPython: No IPython engines "
                        "detected!")
            dview = rc[:]
        except Exception, error:
            msg = "Exception while loading IPython: '%s'" %str(error)
            raise ModuleError(self, msg)

        # initializes each engine
        # importing modules and initializing the VisTrails application
        # in the engines *only* in the first execution on this engine
        uninitialized = []
        for eng in engines:
            try:
                rc[eng]['init']
            except:
                uninitialized.append(eng)
        if uninitialized:
            init_view = rc[uninitialized]
            with init_view.sync_imports():
                import tempfile
                import inspect

                # VisTrails API
                import vistrails
                import vistrails.core
                import vistrails.core.db.action
                import vistrails.core.application
                import vistrails.core.modules.module_registry
                from vistrails.core.db.io import serialize
                from vistrails.core.vistrail.vistrail import Vistrail
                from vistrails.core.vistrail.pipeline import Pipeline
                from vistrails.core.db.locator import XMLFileLocator
                from vistrails.core.vistrail.controller import VistrailController
                from vistrails.core.interpreter.default import get_default_interpreter

            # initializing a VisTrails application
            init_view.execute('app = vistrails.core.application.init(args=[])',
                          block=True)

            init_view['init'] = True

        # setting computing color
        module.logging.set_computing(module)

        # executing function in engines
        # each map returns a dictionary
        try:
            map_result = dview.map_sync(execute_wf, workflows, [nameOutput]*len(workflows))
        except Exception, error:
            msg = "Exception while executing in the IPython engines: '%s'" %str(error)
            raise ModuleError(self, msg)

        # verifying errors
        errors = []
        for engine in range(len(map_result)):
            if map_result[engine]['errors']:
                msg = "ModuleError in engine %d: '%s'" %(engine, ', '.join(map_result[engine]['errors']))
                errors.append(msg)

        if errors:
            raise ModuleError(self, '\n'.join(errors))

        # setting success color
        module.logging.signalSuccess(module)

        # getting the value of the output ports
        # here, we get the first map execution to check the name of the output
        # ports, as they are the same among the map executions
        first_map_execution = map_result[0]
        output_ports = first_map_execution['ports']

        # checking if the value of some output port was not obtained
        diff = list(set(nameOutput) - set(output_ports))

        if diff != []:
            ports = ', '.join(diff)
            raise ModuleError(self,
                              'Output ports not found: %s' %ports)

        import vistrails.core.modules.module_registry
        reg = vistrails.core.modules.module_registry.get_module_registry()
        self.result = []
        for map_execution in map_result:
            execution_output = []
            serializable = map_execution['serializable']
            for i in range(len(map_execution['outputs'])):
                output = None
                if not serializable[i]:
                    output = map_execution['outputs'][i]
                else:
                    d_tuple = vistrails.core.modules.utils.parse_descriptor_string(serializable[i])
                    d = reg.get_descriptor_by_name(*d_tuple)
                    module_klass = d.module
                    output = module_klass().deserialize(map_execution['outputs'][i])
                execution_output.append(output)
            self.result.append(execution_output)

        # including execution logs
        for engine in range(len(map_result)):
            log = map_result[engine]['xml_log']
            exec_ = None
            if (vtType == 'abstraction') or (vtType == 'group'):
                exec_ = unserialize(log, GroupExec)
            elif (vtType == 'module'):
                exec_ = unserialize(log, ModuleExec)
            else:
                # something is wrong...
                continue

            # assigning new ids to existing annotations
            exec_annotations = exec_.annotations
            for i in range(len(exec_annotations)):
                exec_annotations[i].id = self.logging.log.log.id_scope.getNewId(Annotation.vtType)

            parallel_annotation = Annotation(key='parallel_execution', value=True)
            parallel_annotation.id = self.logging.log.log.id_scope.getNewId(Annotation.vtType)
            annotations = [parallel_annotation] + exec_annotations
            exec_.annotations = annotations

            # before adding the execution log, we need to get the machine information
            machine = unserialize(map_result[engine]['machine_log'], Machine)
            machine.id = self.logging.log.log.id_scope.getNewId(Machine.vtType) #assigning new id
            self.logging.log.log.add_machine(machine)

            # recursively add machine information to execution items
            def add_machine_recursive(exec_):
                for i in range(len(exec_.item_execs)):
                    if hasattr(exec_.item_execs[i], 'machine_id'):
                        exec_.item_execs[i].machine_id = machine.id
                        vt_type = exec_.item_execs[i].vtType
                        if (vt_type == 'abstraction') or (vt_type == 'group'):
                            add_machine_resursive(exec_.item_execs[i])

            exec_.machine_id = machine.id
            if (vtType == 'abstraction') or (vtType == 'group'):
                add_machine_recursive(exec_)

            self.logging.add_exec(exec_)


    def serialize_module(self, module):
        """
        Serializes a module to be executed in parallel.
        """

        def process_group(group):
            group.pipeline.id = None
            for module in group.pipeline.module_list:
                if module.is_group():
                    process_group(module)

        pipeline = Pipeline(version=vistrails.db.versions.currentVersion)

        if module.is_group():
            process_group(module)

        module = module.do_copy()
        pipeline.add_module(module)

        return serialize(pipeline)

    def setInputValues(self, module, inputPorts, elementList):
        """
        Function used to set a value inside 'module', given the input port(s).
        """
        for element, inputPort in izip(elementList, inputPorts):
            ## Cleaning the previous connector...
            if inputPort in module.inputPorts:
                del module.inputPorts[inputPort]
            new_connector = ModuleConnector(create_constant(element), 'value')
            module.set_input_port(inputPort, new_connector)

    def typeChecking(self, module, inputPorts, inputList):
        """
        Function used to check if the types of the input list element and of the
        inputPort of 'module' match.
        """
        for elementList in inputList:
            if len(elementList) != len(inputPorts):
                raise ModuleError(self,
                                  'The number of input values and input ports '
                                  'are not the same.')
            for element, inputPort in izip(elementList, inputPorts):
                p_modules = module.moduleInfo['pipeline'].modules
                p_module = p_modules[module.moduleInfo['moduleId']]
                port_spec = p_module.get_port_spec(inputPort, 'input')
                v_module = create_module(element, port_spec.signature)
                if v_module is not None:
                    if not self.compare(port_spec, v_module, inputPort):
                        raise ModuleError(self,
                                          'The type of a list element does '
                                          'not match with the type of the '
                                          'port %s.' % inputPort)

                    del v_module
                else:
                    break

    def createSignature(self, v_module):
        """
    `   Function used to create a signature, given v_module, for a port spec.
        """
        if type(v_module)==tuple:
            v_module_class = []
            for module_ in v_module:
                v_module_class.append(self.createSignature(module_))
            return v_module_class
        else:
            return v_module.__class__

    def compare(self, port_spec, v_module, port):
        """
        Function used to compare two port specs.
        """
        port_spec1 = port_spec

        from vistrails.core.modules.module_registry import get_module_registry
        reg = get_module_registry()

        from vistrails.core.vistrail.port_spec import PortSpec
        v_module = self.createSignature(v_module)
        port_spec2 = PortSpec(**{'signature': v_module})
        matched = reg.are_specs_matched(port_spec2, port_spec1)

        return matched

    def compute(self):
        """The compute method for Map."""

        self.result = None
        self.updateFunctionPort()

        self.setResult('Result', self.result)

#################################################################################

class NewConstant(Constant):
    """
    A new Constant module to be used inside the Map module.
    """
    def setValue(self, v):
        self.setResult("value", v)
        self.upToDate = True

def create_constant(value):
    """
    Creates a NewConstant module, to be used for the ModuleConnector.
    """
    constant = NewConstant()
    constant.setValue(value)
    return constant

def create_module(value, signature):
    """
    Creates a module for value, in order to do the type checking.
    """

    from vistrails.core.modules.basic_modules import Boolean, String, Integer, Float, Tuple, File, List

    if type(value)==bool:
        v_module = Boolean()
        return v_module
    elif type(value)==str:
        v_module = String()
        return v_module
    elif type(value)==int:
        if type(signature)==list:
            signature = signature[0]
        if signature[0]==Float().__class__:
            v_module = Float()
        else:
            v_module = Integer()
        return v_module
    elif type(value)==float:
        v_module = Float()
        return v_module
    elif type(value)==list:
        v_module = List()
        return v_module
    elif type(value)==file:
        v_module = File()
        return v_module
    elif type(value)==tuple:
        v_modules = ()
        for element in xrange(len(value)):
            v_modules += (create_module(value[element], signature[element]),)
        return v_modules
    else:
        from vistrails.core import debug
        debug.warning("Could not identify the type of the list element.")
        debug.warning("Type checking is not going to be done inside Map module.")
        return None

