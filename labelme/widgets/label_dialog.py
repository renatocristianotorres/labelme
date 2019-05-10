from qtpy import QT_VERSION
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

QT5 = QT_VERSION[0] == '5'  # NOQA

from labelme.logger import logger
import labelme.utils


# TODO(unknown):
# - Calculate optimal position so as not to go out of screen area.


class LabelQLineEdit(QtWidgets.QLineEdit):

    def setListWidget(self, list_widget):
        self.list_widget = list_widget

    def keyPressEvent(self, e):
        if e.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down]:
            self.list_widget.keyPressEvent(e)
        else:
            super(LabelQLineEdit, self).keyPressEvent(e)


class LabelDialog(QtWidgets.QDialog):

    def __init__(self, text="Enter object label", parent=None, labels=None,
                 sort_labels=True, show_text_field=True,
                 completion='startswith', fit_to_content=None, flags=None):
        if fit_to_content is None:
            fit_to_content = {'row': False, 'column': True}
        self._fit_to_content = fit_to_content

        super(LabelDialog, self).__init__(parent)
        self.edit = LabelQLineEdit()
        self.edit.setPlaceholderText(text)
        self.edit.setValidator(labelme.utils.labelValidator())
        self.edit.editingFinished.connect(self.postProcess)
        if flags:
            self.edit.textChanged.connect(self.updateFlags)
        layout = QtWidgets.QVBoxLayout()
        if show_text_field:
            layout.addWidget(self.edit)
        # buttons
        self.buttonBox = bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self,
        )
        bb.button(bb.Ok).setIcon(labelme.utils.newIcon('done'))
        bb.button(bb.Cancel).setIcon(labelme.utils.newIcon('undo'))
        bb.accepted.connect(self.validate)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)
        # label_list
        self.labelList = QtWidgets.QListWidget()
        if self._fit_to_content['row']:
            self.labelList.setHorizontalScrollBarPolicy(
                QtCore.Qt.ScrollBarAlwaysOff
            )
        if self._fit_to_content['column']:
            self.labelList.setVerticalScrollBarPolicy(
                QtCore.Qt.ScrollBarAlwaysOff
            )
        self._sort_labels = sort_labels
        if labels:
            self.labelList.addItems(labels)
        if self._sort_labels:
            self.labelList.sortItems()
        else:
            self.labelList.setDragDropMode(
                QtWidgets.QAbstractItemView.InternalMove)
        self.labelList.currentItemChanged.connect(self.labelSelected)
        self.edit.setListWidget(self.labelList)
        layout.addWidget(self.labelList)
        # label_flags
        self.flags = flags
        self.label_flags = None
        if flags:
            self.label_flags = QtWidgets.QVBoxLayout()
            self.resetFlags()
            layout.addItem(self.label_flags)
        self.setLayout(layout)
        # completion
        completer = QtWidgets.QCompleter()
        if not QT5 and completion != 'startswith':
            logger.warn(
                "completion other than 'startswith' is only "
                "supported with Qt5. Using 'startswith'"
            )
            completion = 'startswith'
        if completion == 'startswith':
            completer.setCompletionMode(QtWidgets.QCompleter.InlineCompletion)
            # Default settings.
            # completer.setFilterMode(QtCore.Qt.MatchStartsWith)
        elif completion == 'contains':
            completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
            completer.setFilterMode(QtCore.Qt.MatchContains)
        else:
            raise ValueError('Unsupported completion: {}'.format(completion))
        completer.setModel(self.labelList.model())
        self.edit.setCompleter(completer)

    def addLabelHistory(self, label):
        if self.labelList.findItems(label, QtCore.Qt.MatchExactly):
            return
        self.labelList.addItem(label)
        if self._sort_labels:
            self.labelList.sortItems()

    def labelSelected(self, item):
        self.edit.setText(item.text())

    def updateFlags(self, text):
        flags = self.getFlags()
        newFlags = {}
        for label in ["__all__", text]:
            if label in self.flags:
                for key in self.flags[label]:
                    newFlags[key] = False if key not in flags else flags[key]
        self.setFlags(newFlags)

    def validate(self):
        text = self.edit.text()
        if hasattr(text, 'strip'):
            text = text.strip()
        else:
            text = text.trimmed()
        if text:
            self.accept()

    def postProcess(self):
        text = self.edit.text()
        if hasattr(text, 'strip'):
            text = text.strip()
        else:
            text = text.trimmed()
        self.edit.setText(text)

    def deleteFlags(self):
        for i in reversed(range(self.label_flags.count())):
            item = self.label_flags.itemAt(i).widget()
            self.label_flags.removeWidget(item)
            item.setParent(None)

    def resetFlags(self, text=''):
        self.deleteFlags()

        # Add all flags
        for label in ["__all__", text]:
            if label in self.flags:
                for key in self.flags[label]:
                    item = QtWidgets.QCheckBox(key, self)
                    self.label_flags.addWidget(item)
                    item.show()

    def setFlags(self, flags, text=''):
        self.deleteFlags()

        # Add flags not set
        for label in ["__all__", text]:
            if label in self.flags:
                for key in self.flags[label]:
                    if key not in flags:
                        item = QtWidgets.QCheckBox(key, self)
                        self.label_flags.addWidget(item)
                        item.show()

        # Add set flags
        for key in flags:
            item = QtWidgets.QCheckBox(key, self)
            item.setChecked(flags[key])
            self.label_flags.addWidget(item)
            item.show()

    def getFlags(self):
        flags = {}
        for i in range(self.label_flags.count()):
            item = self.label_flags.itemAt(i).widget()
            flags[item.text()] = True if item.isChecked() else False
        return flags

    def popUp(self, text=None, move=True, flags=None):
        if self._fit_to_content['row']:
            self.labelList.setMinimumHeight(
                self.labelList.sizeHintForRow(0) * self.labelList.count() + 2
            )
        if self._fit_to_content['column']:
            self.labelList.setMinimumWidth(
                self.labelList.sizeHintForColumn(0) + 2
            )
        # if text is None, the previous label in self.edit is kept
        if text is None:
            text = self.edit.text()
        if self.label_flags:
            if flags:
                self.setFlags(flags)
            else:
                self.resetFlags(text)
        self.edit.setText(text)
        self.edit.setSelection(0, len(text))
        items = self.labelList.findItems(text, QtCore.Qt.MatchFixedString)
        if items:
            if len(items) != 1:
                logger.warning("Label list has duplicate '{}'".format(text))
            self.labelList.setCurrentItem(items[0])
            row = self.labelList.row(items[0])
            self.edit.completer().setCurrentRow(row)
        self.edit.setFocus(QtCore.Qt.PopupFocusReason)
        if move:
            self.move(QtGui.QCursor.pos())
        if self.exec_():
            return self.edit.text(), self.getFlags() if self.flags else None
        else:
            return None, None
