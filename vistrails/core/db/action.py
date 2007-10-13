############################################################################
##
## Copyright (C) 2006-2007 University of Utah. All rights reserved.
##
## This file is part of VisTrails.
##
## This file may be used under the terms of the GNU General Public
## License version 2.0 as published by the Free Software Foundation
## and appearing in the file LICENSE.GPL included in the packaging of
## this file.  Please review the following to ensure GNU General Public
## Licensing requirements will be met:
## http://www.opensource.org/licenses/gpl-license.php
##
## If you are unsure which license is appropriate for your use (for
## instance, you are interested in developing a commercial derivative
## of VisTrails), please contact us at vistrails@sci.utah.edu.
##
## This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
## WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
##
############################################################################

from core.vistrail.location import Location
import db.services.action

def create_action(action_list):
    from core.vistrail.action import Action
    action = db.services.action.create_action(action_list)
    Action.convert(action)
    return action

def create_action_from_ops(op_list):
    from core.vistrail.action import Action
    action = db.services.action.create_action_from_ops(op_list)
    Action.convert(action)
    return action

def create_paste_action(pipeline, id_scope, id_remap=None):
    action_list = []
    if id_remap is None:
        id_remap = {}
    for module in pipeline.modules.itervalues():
        module.location = Location(id=id_scope.getNewId(Location.vtType),
                                   x=module.location.x + 10.0,
                                   y=module.location.y + 10.0)
        module = module.do_copy(True, id_scope, id_remap)
        action_list.append(('add', module))
    for connection in pipeline.connections.itervalues():
        connection = connection.do_copy(True, id_scope, id_remap)
        action_list.append(('add', connection))
    return create_action(action_list)

