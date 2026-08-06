"""PySide6 prototype for inspecting Football Manager skin bundles."""

from __future__ import annotations

import sys
import traceback
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from fmparser.bundleFilter import assetsFilter
from fmparser.bundles import BundleError, UnityPyBundleReader
from fmparser.structures import AssetData, AssetInfo, AssetReference, BundleInfo

try:
    from PySide6.QtCore import (
        QAbstractTableModel,
        QModelIndex,
        QObject,
        QSettings,
        QSortFilterProxyModel,
        Qt,
        QRunnable,
        QThreadPool,
        Signal,
        Slot,
    )
    from PySide6.QtGui import QAction, QKeySequence
    from PySide6.QtWidgets import (
        QApplication,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QSplitter,
        QStatusBar,
        QTabWidget,
        QTableView,
        QToolBar,
        QVBoxLayout,
        QWidget,
    )
except ImportError as error:  # pragma: no cover - exercised only without optional dependency.
    raise BundleError("PySide6 is required for the Qt prototype. Install with `pip install .[gui]`.") from error


class AssetTableModel(QAbstractTableModel):
    """Qt table model for bundle asset metadata."""

    COLUMNS = ("Path ID", "Name", "Type", "Container", "Size", "References")

    def __init__(self, assets: Sequence[AssetInfo] | None = None) -> None:
        super().__init__()
        self._assets = list(assets or ())

    def assetsSet(self, assets: Sequence[AssetInfo]) -> None:
        self.beginResetModel()
        self._assets = list(assets)
        self.endResetModel()

    def assetAt(self, row: int) -> AssetInfo | None:
        if row < 0 or row >= len(self._assets):
            return None
        return self._assets[row]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._assets)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.UserRole):
            return None
        asset = self._assets[index.row()]
        values = (
            asset.path_id,
            asset.asset_name or "",
            asset.asset_type,
            asset.container_path or "",
            asset.serialized_size if asset.serialized_size is not None else "",
            len(asset.dependencies) + len(asset.external_references),
        )
        return values[index.column()]

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        reverse = order == Qt.SortOrder.DescendingOrder
        self.layoutAboutToBeChanged.emit()
        self._assets.sort(key=lambda asset: _sortValue(asset, column), reverse=reverse)
        self.layoutChanged.emit()


class AssetFilterProxyModel(QSortFilterProxyModel):
    """Filter asset rows by text and optional type text."""

    def __init__(self) -> None:
        super().__init__()
        self._text = ""
        self._asset_type = ""
        self._serialized_text_by_id: dict[int, str] = {}

    def filtersSet(self, *, text: str, asset_type: str) -> None:
        self._text = text
        self._asset_type = asset_type
        self._invalidate()

    def serializedSearchTextSet(self, values: dict[int, str]) -> None:
        self._serialized_text_by_id = dict(values)
        self._invalidate()

    def _invalidate(self) -> None:
        if hasattr(self, "invalidate"):
            self.invalidate()
        else:  # pragma: no cover - compatibility with older PySide6 releases.
            self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        model = self.sourceModel()
        if not isinstance(model, AssetTableModel):
            return True
        asset = model.assetAt(source_row)
        if asset is None:
            return False
        if not assetsFilter((asset,), text="", asset_type=self._asset_type):
            return False
        query = self._text.strip().casefold()
        if not query:
            return True
        if assetsFilter((asset,), text=self._text, asset_type=""):
            return True
        return query in self._serialized_text_by_id.get(asset.path_id, "")


class ReferenceTableModel(QAbstractTableModel):
    """Qt table model for asset references."""

    COLUMNS = ("Path ID", "Type", "Name", "Relationship")

    def __init__(self, references: Sequence[AssetReference] | None = None) -> None:
        super().__init__()
        self._references = list(references or ())

    def referencesSet(self, references: Sequence[AssetReference]) -> None:
        self.beginResetModel()
        self._references = list(references)
        self.endResetModel()

    def referenceAt(self, row: int) -> AssetReference | None:
        if row < 0 or row >= len(self._references):
            return None
        return self._references[row]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._references)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.UserRole):
            return None
        reference = self._references[index.row()]
        values = (
            reference.path_id if reference.path_id is not None else "",
            reference.asset_type or "",
            reference.asset_name or reference.asset_path or reference.external or "",
            reference.relationship or "",
        )
        return values[index.column()]

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        reverse = order == Qt.SortOrder.DescendingOrder
        self.layoutAboutToBeChanged.emit()
        self._references.sort(key=lambda reference: _referenceSortValue(reference, column), reverse=reverse)
        self.layoutChanged.emit()


class _OpenSignals(QObject):
    finished = Signal(object, object, object)
    failed = Signal(str, str)


class _OpenBundleWorker(QRunnable):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.signals = _OpenSignals()

    @Slot()
    def run(self) -> None:
        try:
            reader = UnityPyBundleReader()
            info = reader.open(self.path)
            assets = tuple(reader.assetsList())
        except Exception as error:  # noqa: BLE001 - send readable dialog plus log detail.
            self.signals.failed.emit(str(error), traceback.format_exc())
            return
        self.signals.finished.emit(info, assets, reader)


class _PreviewSignals(QObject):
    finished = Signal(object)
    failed = Signal(str, str)


class _PreviewWorker(QRunnable):
    def __init__(self, reader: UnityPyBundleReader, asset_id: int) -> None:
        super().__init__()
        self.reader = reader
        self.asset_id = asset_id
        self.signals = _PreviewSignals()

    @Slot()
    def run(self) -> None:
        try:
            data = self.reader.assetRead(self.asset_id)
        except Exception as error:  # noqa: BLE001 - send readable dialog plus log detail.
            self.signals.failed.emit(str(error), traceback.format_exc())
            return
        self.signals.finished.emit(data)


class _DeepSearchSignals(QObject):
    finished = Signal(int, object)
    failed = Signal(str, str)


class _DeepSearchWorker(QRunnable):
    def __init__(
        self,
        reader: UnityPyBundleReader,
        assets: Sequence[AssetInfo],
        generation: int,
    ) -> None:
        super().__init__()
        self.reader = reader
        self.assets = tuple(assets)
        self.generation = generation
        self.signals = _DeepSearchSignals()

    @Slot()
    def run(self) -> None:
        try:
            values = {
                asset.path_id: self.reader.assetSearchText(asset.path_id)
                for asset in self.assets
            }
        except Exception as error:  # noqa: BLE001 - send readable dialog plus log detail.
            self.signals.failed.emit(str(error), traceback.format_exc())
            return
        self.signals.finished.emit(self.generation, values)


class _ReferencesSignals(QObject):
    finished = Signal(int, object, object)
    failed = Signal(str, str)


class _ReferencesWorker(QRunnable):
    def __init__(self, reader: UnityPyBundleReader, asset_id: int, generation: int) -> None:
        super().__init__()
        self.reader = reader
        self.asset_id = asset_id
        self.generation = generation
        self.signals = _ReferencesSignals()

    @Slot()
    def run(self) -> None:
        try:
            references = self.reader.assetReferences(self.asset_id)
        except Exception as error:  # noqa: BLE001 - send readable dialog plus log detail.
            self.signals.failed.emit(str(error), traceback.format_exc())
            return
        self.signals.finished.emit(self.generation, self.asset_id, references)


class _ReferenceIndexSignals(QObject):
    finished = Signal(int)
    failed = Signal(str, str)


class _ReferenceIndexWorker(QRunnable):
    def __init__(self, reader: UnityPyBundleReader, generation: int) -> None:
        super().__init__()
        self.reader = reader
        self.generation = generation
        self.signals = _ReferenceIndexSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.reader.referencesBuild()
        except Exception as error:  # noqa: BLE001 - send readable dialog plus log detail.
            self.signals.failed.emit(str(error), traceback.format_exc())
            return
        self.signals.finished.emit(self.generation)


class BundleExplorerWindow(QMainWindow):
    """Initial read-only bundle explorer window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FM26 Skin Bundle Explorer")
        self._settings = QSettings("myHandbook", "fmparser-bundle-explorer")
        self._thread_pool = QThreadPool.globalInstance()
        self._reader: UnityPyBundleReader | None = None
        self._bundle_path: Path | None = None
        self._assets: tuple[AssetInfo, ...] = ()
        self._selected_asset_id: int | None = None
        self._history: list[int] = []
        self._history_index = -1
        self._history_replaying = False
        self._deep_search_generation = 0
        self._deep_search_running = False

        self._model = AssetTableModel()
        self._proxy = AssetFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._table.selectionModel().currentRowChanged.connect(self._assetSelected)

        self._references_model = ReferenceTableModel()
        self._references = QTableView()
        self._references.setModel(self._references_model)
        self._references.setSortingEnabled(True)
        self._references.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._references.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._references.doubleClicked.connect(self._referenceActivated)
        self._reverse_references_model = ReferenceTableModel()
        self._reverse_references = QTableView()
        self._reverse_references.setModel(self._reverse_references_model)
        self._reverse_references.setSortingEnabled(True)
        self._reverse_references.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._reverse_references.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._reverse_references.doubleClicked.connect(self._reverseReferenceActivated)

        self._filter = QLineEdit()
        self._filter.setPlaceholderText("Filter name, type, container, or path ID")
        self._filter.textChanged.connect(self._filtersChanged)
        self._type_filter = QLineEdit()
        self._type_filter.setPlaceholderText("Type filter")
        self._type_filter.textChanged.connect(self._filtersChanged)
        self._type_summary = QListWidget()
        self._type_summary.setMaximumHeight(130)
        self._type_summary.itemClicked.connect(self._typeSummaryClicked)

        self._metadata = QPlainTextEdit()
        self._metadata.setReadOnly(True)
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)

        self._actionsBuild()
        self._layoutBuild()
        self.setStatusBar(QStatusBar())
        self._settingsRestore()

    def bundleOpen(self, path: Path) -> None:
        self._busySet(f"Opening {path}")
        worker = _OpenBundleWorker(path)
        worker.signals.finished.connect(self._bundleOpened)
        worker.signals.failed.connect(self._workerFailed)
        self._thread_pool.start(worker)

    def bundleClose(self) -> None:
        self._reader = None
        self._bundle_path = None
        self._assets = ()
        self._selected_asset_id = None
        self._historyClear()
        self._deep_search_generation += 1
        self._deep_search_running = False
        self._model.assetsSet(())
        self._proxy.serializedSearchTextSet({})
        self._references_model.referencesSet(())
        self._reverse_references_model.referencesSet(())
        self._typeSummarySet(())
        self._metadata.clear()
        self._preview.clear()
        self.statusBar().showMessage("Bundle closed")

    def _actionsBuild(self) -> None:
        toolbar = QToolBar("Bundle")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_action = QAction("Open Bundle", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._bundleChoose)
        toolbar.addAction(open_action)

        close_action = QAction("Close Bundle", self)
        close_action.triggered.connect(self.bundleClose)
        toolbar.addAction(close_action)

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._bundleRefresh)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()
        self._back_action = QAction("Back", self)
        self._back_action.triggered.connect(self._historyBack)
        toolbar.addAction(self._back_action)

        self._forward_action = QAction("Forward", self)
        self._forward_action.triggered.connect(self._historyForward)
        toolbar.addAction(self._forward_action)
        self._historyActionsUpdate()

        copy_action = QAction("Copy Metadata", self)
        copy_action.triggered.connect(self._metadataCopy)
        toolbar.addAction(copy_action)

        export_graph_action = QAction("Export Graph", self)
        export_graph_action.triggered.connect(self._graphExport)
        toolbar.addAction(export_graph_action)

    def _layoutBuild(self) -> None:
        filters = QHBoxLayout()
        filters.addWidget(QLabel("Search"))
        filters.addWidget(self._filter, 2)
        filters.addWidget(QLabel("Type"))
        filters.addWidget(self._type_filter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addLayout(filters)
        left_layout.addWidget(self._type_summary)
        left_layout.addWidget(self._table)

        right = QSplitter(Qt.Orientation.Vertical)
        tabs = QTabWidget()
        tabs.addTab(self._metadata, "Metadata")
        tabs.addTab(self._preview, "Serialized Preview")
        tabs.addTab(self._references, "References")
        tabs.addTab(self._reverse_references, "Referenced By")
        right.addWidget(tabs)
        right.addWidget(self._log)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([750, 450])
        self.setCentralWidget(splitter)

    def _settingsRestore(self) -> None:
        geometry = self._settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        else:
            self.resize(1200, 760)

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("last_bundle_dir", str(self._bundle_path.parent) if self._bundle_path else "")
        super().closeEvent(event)

    def _bundleChoose(self) -> None:
        start = str(self._settings.value("last_bundle_dir", ""))
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Unity Bundle",
            start,
            "Unity bundles (*.bundle);;All files (*)",
        )
        if file_name:
            self.bundleOpen(Path(file_name))

    def _bundleRefresh(self) -> None:
        if self._bundle_path is not None:
            self.bundleOpen(self._bundle_path)

    def _filtersChanged(self) -> None:
        self._proxy.filtersSet(text=self._filter.text(), asset_type=self._type_filter.text())
        self._deepSearchMaybeStart()

    def _typeSummaryClicked(self, item: QListWidgetItem) -> None:
        asset_type = item.data(Qt.ItemDataRole.UserRole)
        self._type_filter.setText(str(asset_type or ""))

    def _assetSelected(self, current: QModelIndex, previous: QModelIndex) -> None:
        del previous
        if self._reader is None or not current.isValid():
            return
        source_index = self._proxy.mapToSource(current)
        asset = self._model.assetAt(source_index.row())
        if asset is None:
            return
        self._selected_asset_id = asset.path_id
        if not self._history_replaying:
            self._historyPush(asset.path_id)
        self._metadata.setPlainText(_metadataText(asset))
        self._preview.setPlainText("Loading preview...")
        self._references_model.referencesSet(())
        self._reverseReferencesRefresh(asset.path_id)
        worker = _PreviewWorker(self._reader, asset.path_id)
        worker.signals.finished.connect(self._previewReady)
        worker.signals.failed.connect(self._workerFailed)
        self._thread_pool.start(worker)
        references_worker = _ReferencesWorker(
            self._reader,
            asset.path_id,
            self._deep_search_generation,
        )
        references_worker.signals.finished.connect(self._referencesReady)
        references_worker.signals.failed.connect(self._workerFailed)
        self._thread_pool.start(references_worker)

    def _referenceActivated(self, index: QModelIndex) -> None:
        source_row = index.row()
        reference = self._references_model.referenceAt(source_row)
        if reference is None or reference.path_id is None:
            return
        self._assetSelectById(reference.path_id)

    def _reverseReferenceActivated(self, index: QModelIndex) -> None:
        source_row = index.row()
        reference = self._reverse_references_model.referenceAt(source_row)
        if reference is None or reference.path_id is None:
            return
        self._assetSelectById(reference.path_id)

    def _metadataCopy(self) -> None:
        QApplication.clipboard().setText(self._metadata.toPlainText())
        self.statusBar().showMessage("Metadata copied", 2500)

    def _graphExport(self) -> None:
        if self._reader is None or self._selected_asset_id is None:
            QMessageBox.information(self, "Bundle Explorer", "Select an asset before exporting a graph.")
            return
        file_name, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Asset Graph",
            "",
            "JSON graph (*.json);;Graphviz DOT (*.dot)",
        )
        if not file_name:
            return
        path = Path(file_name)
        format_name = "dot" if "DOT" in selected_filter or path.suffix.casefold() == ".dot" else "json"
        if not path.suffix:
            path = path.with_suffix(f".{format_name}")
        text = self._reader.assetGraphText(self._selected_asset_id, format_name)
        path.write_text(text, encoding="utf-8")
        self.statusBar().showMessage(f"Exported graph to {path}", 2500)

    def _bundleOpened(
        self,
        info: BundleInfo,
        assets: tuple[AssetInfo, ...],
        reader: UnityPyBundleReader,
    ) -> None:
        self._reader = reader
        self._bundle_path = info.path
        self._assets = assets
        self._deep_search_generation += 1
        self._deep_search_running = False
        self._historyClear()
        self._settings.setValue("last_bundle_dir", str(info.path.parent))
        self._model.assetsSet(assets)
        self._proxy.serializedSearchTextSet({})
        self._references_model.referencesSet(())
        self._reverse_references_model.referencesSet(())
        self._typeSummarySet(assets)
        self._metadata.setPlainText(_bundleText(info))
        self._preview.clear()
        self._log.appendPlainText(f"Opened {info.file_name}: {info.asset_count} assets")
        self.statusBar().showMessage(f"Opened {info.file_name}")
        self._referenceIndexStart()

    def _previewReady(self, data: AssetData) -> None:
        self._metadata.setPlainText(_metadataText(data.asset))
        preview = data.text or data.message or "No readable preview is available."
        if data.message and data.text:
            preview = f"{data.message}\n\n{data.text}"
        self._preview.setPlainText(preview)
        self.statusBar().showMessage(f"Selected asset {data.asset.path_id}", 2500)

    def _workerFailed(self, message: str, detail: str) -> None:
        self._log.appendPlainText(detail)
        self.statusBar().showMessage("Bundle operation failed")
        QMessageBox.warning(self, "Bundle Explorer", message)

    def _busySet(self, message: str) -> None:
        self.statusBar().showMessage(message)
        self._log.appendPlainText(message)

    def _deepSearchMaybeStart(self) -> None:
        if self._reader is None or self._deep_search_running or not self._filter.text().strip():
            return
        self._deep_search_running = True
        generation = self._deep_search_generation
        worker = _DeepSearchWorker(self._reader, self._assets, generation)
        worker.signals.finished.connect(self._deepSearchReady)
        worker.signals.failed.connect(self._workerFailed)
        self._thread_pool.start(worker)
        self.statusBar().showMessage("Building serialized search cache...")

    def _deepSearchReady(self, generation: int, values: dict[int, str]) -> None:
        if generation != self._deep_search_generation:
            return
        self._deep_search_running = False
        self._proxy.serializedSearchTextSet(values)
        self.statusBar().showMessage("Serialized search cache ready", 2500)

    def _referencesReady(
        self,
        generation: int,
        asset_id: int,
        references: tuple[AssetReference, ...],
    ) -> None:
        if generation != self._deep_search_generation:
            return
        if asset_id != self._selected_asset_id:
            return
        self._references_model.referencesSet(references)
        self.statusBar().showMessage(f"Loaded {len(references)} references for {asset_id}", 2500)

    def _referenceIndexStart(self) -> None:
        if self._reader is None:
            return
        worker = _ReferenceIndexWorker(self._reader, self._deep_search_generation)
        worker.signals.finished.connect(self._referenceIndexReady)
        worker.signals.failed.connect(self._workerFailed)
        self._thread_pool.start(worker)
        self.statusBar().showMessage("Building reverse reference index...")

    def _referenceIndexReady(self, generation: int) -> None:
        if generation != self._deep_search_generation:
            return
        if self._selected_asset_id is not None:
            self._reverseReferencesRefresh(self._selected_asset_id)
        self.statusBar().showMessage("Reverse reference index ready", 2500)

    def _reverseReferencesRefresh(self, asset_id: int) -> None:
        if self._reader is None:
            self._reverse_references_model.referencesSet(())
            return
        self._reverse_references_model.referencesSet(self._reader.reverseReferences(asset_id))

    def _assetSelectById(self, path_id: int, *, add_history: bool = True) -> None:
        for row in range(self._model.rowCount()):
            asset = self._model.assetAt(row)
            if asset is None or asset.path_id != path_id:
                continue
            source_index = self._model.index(row, 0)
            proxy_index = self._proxy.mapFromSource(source_index)
            if proxy_index.isValid():
                previous = self._history_replaying
                self._history_replaying = not add_history
                try:
                    self._table.setCurrentIndex(proxy_index)
                    self._table.scrollTo(proxy_index)
                finally:
                    self._history_replaying = previous
            return

    def _historyPush(self, path_id: int) -> None:
        if self._history_index >= 0 and self._history[self._history_index] == path_id:
            return
        if self._history_index < len(self._history) - 1:
            self._history = self._history[: self._history_index + 1]
        self._history.append(path_id)
        self._history_index = len(self._history) - 1
        self._historyActionsUpdate()

    def _historyBack(self) -> None:
        if self._history_index <= 0:
            return
        self._history_index -= 1
        self._historyActionsUpdate()
        self._assetSelectById(self._history[self._history_index], add_history=False)

    def _historyForward(self) -> None:
        if self._history_index >= len(self._history) - 1:
            return
        self._history_index += 1
        self._historyActionsUpdate()
        self._assetSelectById(self._history[self._history_index], add_history=False)

    def _historyClear(self) -> None:
        self._history = []
        self._history_index = -1
        self._historyActionsUpdate()

    def _historyActionsUpdate(self) -> None:
        back_action = getattr(self, "_back_action", None)
        forward_action = getattr(self, "_forward_action", None)
        if back_action is not None:
            back_action.setEnabled(self._history_index > 0)
        if forward_action is not None:
            forward_action.setEnabled(self._history_index < len(self._history) - 1)

    def _typeSummarySet(self, assets: Sequence[AssetInfo]) -> None:
        self._type_summary.clear()
        for asset_type, count in _typeCounts(assets):
            item = QListWidgetItem(f"{asset_type:<24} {count}")
            item.setData(Qt.ItemDataRole.UserRole, asset_type)
            self._type_summary.addItem(item)


def main(argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv[:1])
    window = BundleExplorerWindow()
    window.show()
    args = argv or []
    if args:
        window.bundleOpen(Path(args[0]))
    return int(app.exec())


def _sortValue(asset: AssetInfo, column: int) -> str | int:
    values: tuple[str | int, ...] = (
        asset.path_id,
        asset.asset_name or "",
        asset.asset_type,
        asset.container_path or "",
        asset.serialized_size if asset.serialized_size is not None else -1,
        len(asset.dependencies) + len(asset.external_references),
    )
    return values[column]


def _typeCounts(assets: Sequence[AssetInfo]) -> tuple[tuple[str, int], ...]:
    counts = Counter(asset.asset_type for asset in assets)
    return tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold())))


def _referenceSortValue(reference: AssetReference, column: int) -> str | int:
    values: tuple[str | int, ...] = (
        reference.path_id if reference.path_id is not None else -1,
        reference.asset_type or "",
        reference.asset_name or reference.asset_path or reference.external or "",
        reference.relationship or "",
    )
    return values[column]


def _bundleText(info: BundleInfo) -> str:
    return "\n".join(
        (
            f"File: {info.file_name}",
            f"Path: {info.path}",
            f"Size: {info.size}",
            f"Signature: {info.signature}",
            f"Unity version: {info.unity_version or 'unknown'}",
            f"Asset count: {info.asset_count}",
            f"External references: {len(info.external_references)}",
        )
    )


def _metadataText(asset: AssetInfo) -> str:
    return "\n".join(
        (
            f"Path ID: {asset.path_id}",
            f"Name: {asset.asset_name or 'unknown'}",
            f"Type: {asset.asset_type}",
            f"Container: {asset.container_path or 'unknown'}",
            f"Serialized size: {asset.serialized_size if asset.serialized_size is not None else 'unknown'}",
            f"References: {len(asset.dependencies) + len(asset.external_references)}",
        )
    )


if __name__ == "__main__":
    sys.exit(main())
