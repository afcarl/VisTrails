###############################################################################
##
## Copyright (C) 2014-2016, New York University.
## Copyright (C) 2013-2014, NYU-Poly.
## All rights reserved.
## Contact: contact@vistrails.org
##
## This file is part of VisTrails.
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are met:
##
##  - Redistributions of source code must retain the above copyright notice,
##    this list of conditions and the following disclaimer.
##  - Redistributions in binary form must reproduce the above copyright
##    notice, this list of conditions and the following disclaimer in the
##    documentation and/or other materials provided with the distribution.
##  - Neither the name of the New York University nor the names of its
##    contributors may be used to endorse or promote products derived from
##    this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
## AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
## THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
## PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
## CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
## EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
## PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
## OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
## WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
## OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
## ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
##
###############################################################################



from PyQt5 import QtCore, QtWidgets


from vistrails.gui.modules.module_configure import \
    StandardModuleConfigurationWidget

from .identifiers import identifier
from vistrails.core.modules.basic_modules import List


class Entry(QtWidgets.QWidget):
    remove = QtCore.pyqtSignal()
    changed = QtCore.pyqtSignal()

    def __init__(self, name):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        self.lineedit = QtWidgets.QLineEdit(name)
        layout.addWidget(QtWidgets.QLabel(self.prefix))
        layout.addWidget(self.lineedit)
        layout.addStretch()
        remove_button = QtWidgets.QPushButton("Remove port")
        remove_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                    QtWidgets.QSizePolicy.Fixed)
        layout.addWidget(remove_button)

        remove_button.clicked.connect(self.remove)
        self.lineedit.textEdited.connect(self.changed)

    @property
    def name(self):
        return self.lineedit.text()


class TableEntry(Entry):
    prefix = "Table input"


class ColumnEntry(Entry):
    prefix = "Single column entry"


class BuildTableWidget(StandardModuleConfigurationWidget):
    """
    Configuration widget allowing to create the ports of the BuildTable module.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Window title
        self.setWindowTitle("Build table configuration")

        central_layout = QtWidgets.QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        self.setLayout(central_layout)

        self._scroll_area = QtWidgets.QScrollArea()
        inner_widget = QtWidgets.QWidget()
        self._list_layout = QtWidgets.QVBoxLayout()
        scroll_layout = QtWidgets.QVBoxLayout()
        scroll_layout.addLayout(self._list_layout)
        scroll_layout.addStretch()
        inner_widget.setLayout(scroll_layout)
        self._scroll_area.setVerticalScrollBarPolicy(
                QtCore.Qt.ScrollBarAlwaysOn)
        self._scroll_area.setWidget(inner_widget)
        self._scroll_area.setWidgetResizable(True)
        central_layout.addWidget(self._scroll_area)

        add_buttons = QtWidgets.QHBoxLayout()
        central_layout.addLayout(add_buttons)
        add_table = QtWidgets.QPushButton("Add a whole table")
        add_table.clicked.connect(self.add_table)
        add_buttons.addWidget(add_table)
        add_column = QtWidgets.QPushButton("Add a list as a single column")
        add_column.clicked.connect(self.add_column)
        add_buttons.addWidget(add_column)

        self.createButtons()

        self.createEntries()

    def add_item(self, item):
        self._list_layout.addWidget(item)
        item.remove.connect(lambda: item.deleteLater())
        item.changed.connect(self.updateState)

    def add_table(self):
        self.add_item(TableEntry(
                "Table #%d" % (self._list_layout.count() + 1)))
        self.updateState()

    def add_column(self):
        self.add_item(ColumnEntry(
                "Column #%d" % (self._list_layout.count() + 1)))
        self.updateState()

    def createButtons(self):
        """ createButtons() -> None
        Create and connect signals to Ok & Cancel button

        """
        buttonLayout = QtWidgets.QHBoxLayout()
        buttonLayout.setContentsMargins(5, 5, 5, 5)
        self.saveButton = QtWidgets.QPushButton("&Save", self)
        self.saveButton.setFixedWidth(100)
        self.saveButton.setEnabled(False)
        buttonLayout.addWidget(self.saveButton)
        self.resetButton = QtWidgets.QPushButton("&Reset", self)
        self.resetButton.setFixedWidth(100)
        self.resetButton.setEnabled(False)
        buttonLayout.addWidget(self.resetButton)
        self.layout().addLayout(buttonLayout)
        self.saveButton.clicked.connect(self.saveTriggered)
        self.resetButton.clicked.connect(self.resetTriggered)

    def saveTriggered(self, checked = False):
        """ saveTriggered(checked: bool) -> None
        Update vistrail controller and module when the user click Ok

        """
        if self.updateVistrail():
            self.saveButton.setEnabled(False)
            self.resetButton.setEnabled(False)
            self.state_changed = False
            self.stateChanged.emit()
            self.doneConfigure.emit(self.module.id)

    def closeEvent(self, event):
        self.askToSaveChanges()
        event.accept()

    def getCurrentPorts(self):
        current_ports = []
        for port_spec in self.module.input_port_specs:
            is_table = port_spec.signature[0][0] is not List
            current_ports.append((port_spec.name, is_table))
        return current_ports

    def updateVistrail(self):
        """ updateVistrail() -> None
        Update Vistrail to contain changes in the port table

        """
        table_sig = '(%s:Table)' % identifier
        list_sig = '(org.vistrails.vistrails.basic:List)'
        seen_new_ports = set()
        current_ports = dict(self.getCurrentPorts())
        add_ports = []
        delete_ports = []
        for i in range(self._list_layout.count()):
            widget = self._list_layout.itemAt(i).widget()
            is_table = isinstance(widget, TableEntry)
            name = widget.name

            if name in seen_new_ports:
                QtWidgets.QMessageBox.critical(
                        self,
                        "Duplicated port name",
                        "There are several input ports with name %r" % name)
                return
            seen_new_ports.add(name)

            if name in current_ports:
                old_is_table = current_ports.pop(name)
                if is_table == old_is_table:
                    continue
                delete_ports.append(('input', name))

            sigstring = table_sig if is_table else list_sig
            add_ports.append(('input', name,
                              sigstring, -1))

        delete_ports.extend(('input', unseen_port)
                            for unseen_port in current_ports.keys())

        self.controller.update_ports(self.module.id, delete_ports, add_ports)

        return True

    def createEntries(self):
        for name, is_table in self.getCurrentPorts():
            if is_table:
                self.add_item(TableEntry(name))
            else:
                self.add_item(ColumnEntry(name))

    def resetTriggered(self, checked = False):
        for i in range(self._list_layout.count()):
            self._list_layout.itemAt(i).widget().deleteLater()

        self.createEntries()

        self.saveButton.setEnabled(False)
        self.resetButton.setEnabled(False)
        self.state_changed = False
        self.stateChanged.emit()

    def updateState(self):
        self.saveButton.setEnabled(True)
        self.resetButton.setEnabled(True)
        if not self.state_changed:
            self.state_changed = True
            self.stateChanged.emit()
