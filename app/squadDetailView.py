"""Editable squad assessment workspace for requirement 007."""

from __future__ import annotations

from dataclasses import replace
from importlib.resources import files

from fmsat.core.logUtils import getLogger
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fmsat.app.squadDetailModel import SquadDetailModel
from fmsat.app.squadDetailTabOverrides import SquadAnalysisTab, SquadPlayersTab, SquadRolesTab
from fmsat.app.squadDetailTabs import SquadOverviewTab
from fmsat.core.config import AttributeDefinition
from fmsat.core.squadModel import SquadModel

logger = getLogger()


class SquadDetailView(QWidget):
    """Coordinate squad facts, editable players, roles, and generated analysis."""

    backRequested = Signal()
    modelSaveRequested = Signal(object)
    modelRegenerateRequested = Signal(str)
    tacticSelected = Signal(str, str)

    def __init__(
        self,
        parent: QWidget | None = None,
        attributes: tuple[AttributeDefinition, ...] = (),
    ) -> None:
        super().__init__(parent)
        self.attributes = attributes
        self.model: SquadDetailModel | None = None
        self.squadName = ""
        self.regenerationProgress: QProgressDialog | None = None
        self.setObjectName("squadDetailView")
        self.setStyleSheet(
            files("fmsat.app").joinpath("fmsat.qss").read_text(encoding="utf-8")
        )
        self.rootLayout = QVBoxLayout(self)
        self.rootLayout.setContentsMargins(28, 20, 28, 24)
        self.rootLayout.setSpacing(16)

    def squadShow(self, squadName: str, model: SquadDetailModel) -> None:
        self.squadName = squadName
        self.model = model
        self._contentRefresh()

    def _contentRefresh(self) -> None:
        self._layoutClear(self.rootLayout)
        if self.model is None:
            return
        self.rootLayout.addLayout(self._headerCreate())
        self.rootLayout.addLayout(self._factsCreate())
        self.rootLayout.addWidget(self._tabsCreate(), 1)
        footer = QHBoxLayout()
        footer.addStretch()
        self.regenerateButton = QPushButton("Regenerate Squad Model")
        self.regenerateButton.setToolTip(
            "Re-read the saved squad screenshots with the current parser and rebuild the squad model."
        )
        self.regenerateButton.clicked.connect(self._regenerateRequest)
        footer.addWidget(self.regenerateButton)
        self.saveButton = QPushButton("Save Player Changes")
        self.saveButton.setToolTip("Save edits made in the Players tab to the squad model.")
        self.saveButton.setEnabled(False)
        self.saveButton.clicked.connect(self._saveRequest)
        footer.addWidget(self.saveButton)
        self.rootLayout.addLayout(footer)

    def _headerCreate(self) -> QHBoxLayout:
        assert self.model is not None
        header = QHBoxLayout()
        back = QPushButton("←  FMSAT Workspace")
        back.setObjectName("quietButton")
        back.clicked.connect(self.backRequested.emit)
        header.addWidget(back)
        heading = QVBoxLayout()
        eyebrow = QLabel("Squad Workspace  ·  Role-Level Assessment")
        eyebrow.setObjectName("eyebrow")
        heading.addWidget(eyebrow)
        title = QLabel(self.squadName)
        title.setObjectName("pageTitle")
        heading.addWidget(title)
        header.addLayout(heading, 1)

        tacticControl = QVBoxLayout()
        tacticControl.setSpacing(3)
        tacticLabel = QLabel("APPLY TACTIC")
        tacticLabel.setObjectName("factKey")
        tacticControl.addWidget(tacticLabel)
        self.tacticPicker = QComboBox()
        self.tacticPicker.setObjectName("squadTacticPicker")
        availableTactics = self._systemTactics()
        tacticAssigned = self.model.tacticName not in {
            "No tactic selected",
            "No tactic assigned",
        }
        current = self.model.tacticName if tacticAssigned else "No tactic assigned"
        self.tacticPicker.addItem(current)
        for tacticName in availableTactics:
            if tacticName != current:
                self.tacticPicker.addItem(tacticName)
        self.tacticPicker.currentTextChanged.connect(self._tacticChange)
        self.tacticPicker.setEnabled(bool(availableTactics))
        tacticControl.addWidget(self.tacticPicker)
        header.addLayout(tacticControl)
        return header

    def _factsCreate(self) -> QHBoxLayout:
        assert self.model is not None
        covered = sum(
            not role.coverage.startswith("Uncovered") for role in self.model.roles
        )
        facts = QHBoxLayout()
        tacticName = (
            "No tactic assigned"
            if self.model.tacticName in {"No tactic selected", "No tactic assigned"}
            else self.model.tacticName
        )
        for label, value in (
            ("PLAYERS", str(len(self.model.squad.players))),
            ("TACTIC", tacticName),
            ("UNIQUE TACTIC ROLES", str(len(self.model.roles))),
            ("COVERED UNIQUE ROLES", f"{covered} of {len(self.model.roles)}"),
            ("STATUS", self.model.sourceStatus),
        ):
            facts.addWidget(self._factCardCreate(label, value), 1)
        return facts

    def _tabsCreate(self) -> QTabWidget:
        assert self.model is not None
        tabs = QTabWidget()
        tabs.setObjectName("squadTabs")
        tabs.addTab(SquadOverviewTab(self.model), "Overview")
        self.playersTab = SquadPlayersTab(self.model.squad, self.attributes)
        self.playersTab.changed.connect(lambda: self.saveButton.setEnabled(True))
        tabs.addTab(self.playersTab, "Players")
        tabs.addTab(SquadRolesTab(self.model.roles, self.attributes), "Roles")
        tabs.addTab(
            SquadAnalysisTab(
                self.model,
                self.attributes,
                self._requiredRoleRows(),
            ),
            "Analysis",
        )
        return tabs

    def _saveRequest(self) -> None:
        model: SquadModel = self.playersTab.modelBuild()
        self.modelSaveRequested.emit(model)

    def _regenerateRequest(self) -> None:
        """Re-OCR retained screenshots without blocking the Qt UI thread."""

        if self.model is None:
            return
        self.regenerateButton.setEnabled(False)
        logger.doing(f"requesting squad model regeneration for {self.squadName}")
        progress = self._regenerationProgressCreate()
        self.regenerationProgress = progress
        progress.show()
        try:
            self.modelRegenerateRequested.emit(self.squadName)
            window = self.window()
            service = getattr(window, "squadModelService", None)
            if service is None:
                return
            regenerationModel = replace(
                self.model.squad,
                regenerationRequired=True,
            )
            backgroundRun = getattr(window, "_backgroundRun", None)
            if callable(backgroundRun):
                backgroundRun(lambda: service.modelSave(regenerationModel))
            else:
                service.modelSave(regenerationModel)
            dataChanged = getattr(window, "dataChanged", None)
            if dataChanged is not None and hasattr(dataChanged, "emit"):
                dataChanged.emit()
            squadShow = getattr(window, "squadShow", None)
            if callable(squadShow):
                squadShow(self.squadName, self.model.tacticName)
            statusBar = getattr(window, "statusBar", None)
            if callable(statusBar):
                statusBar().showMessage(
                    f"Regenerated {self.squadName} from saved screenshot evidence.",
                    10000,
                )
        except Exception as exc:
            logger.exception("unable to regenerate squad model %r", self.squadName)
            statusBar = getattr(self.window(), "statusBar", None)
            if callable(statusBar):
                statusBar().showMessage(str(exc), 10000)
        finally:
            progress.close()
            self.regenerateButton.setEnabled(True)

    def _regenerationProgressCreate(self) -> QProgressDialog:
        progress = QProgressDialog(
            "Regenerating squad model from saved screenshot evidence…",
            None,
            0,
            0,
            self,
        )
        progress.setObjectName("squadRegenerationProgressDialog")
        progress.setWindowTitle("Regenerate Squad Model")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumWidth(560)
        progress.setMinimumHeight(140)
        progress.resize(560, 140)
        progress.setStyleSheet(
            "QProgressDialog#squadRegenerationProgressDialog { background-color: #101f2e; color: #e8eef5; } "
            "QProgressDialog#squadRegenerationProgressDialog QLabel { background: transparent; color: #e8eef5; font-size: 14px; font-weight: 600; padding: 12px 10px; min-height: 34px; } "
            "QProgressDialog#squadRegenerationProgressDialog QProgressBar { background-color: #08131f; color: #e8eef5; border: 1px solid #30465a; border-radius: 7px; min-height: 24px; text-align: center; } "
            "QProgressDialog#squadRegenerationProgressDialog QProgressBar::chunk { background-color: #31b98f; border-radius: 6px; }"
        )
        return progress

    def _tacticChange(self, choice: str) -> None:
        if (
            self.model is None
            or choice in {"", "No tactic assigned"}
            or choice == self.model.tacticName
        ):
            return
        if choice == "Assign tactic…":
            selected = self._tacticAssignmentSelect()
            if selected is not None:
                self._tacticAssign(selected)
            return
        self._tacticAssign(choice)

    def _tacticAssignmentSelect(self) -> str | None:
        tactics = self._systemTactics()
        if not tactics:
            return None
        dialog = QDialog(self)
        dialog.setWindowTitle("Assign tactic")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Choose an existing tactic to assign to this squad:"))
        picker = QComboBox(dialog)
        picker.addItems(tactics)
        layout.addWidget(picker)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return picker.currentText().strip() or None

    def _tacticAssign(self, tacticName: str) -> None:
        database = getattr(self.window(), "database", None)
        if database is not None:
            try:
                database.tacticApplyToSquad(self.squadName, tacticName)
                logger.action(
                    "squad tactic selected squad=%r tactic=%r",
                    self.squadName,
                    tacticName,
                )
                dataChanged = getattr(self.window(), "dataChanged", None)
                if dataChanged is not None and hasattr(dataChanged, "emit"):
                    dataChanged.emit()
            except Exception as exc:
                logger.exception(
                    "unable to assign tactic from squad workspace squad=%r tactic=%r",
                    self.squadName,
                    tacticName,
                )
                statusBar = getattr(self.window(), "statusBar", None)
                if callable(statusBar):
                    statusBar().showMessage(str(exc), 10000)
                return
        self.tacticSelected.emit(self.squadName, tacticName)

    def _systemTactics(self) -> tuple[str, ...]:
        assert self.model is not None
        names = set(self.model.availableTactics)
        database = getattr(self.window(), "database", None)
        if database is not None:
            try:
                names.update(database.tacticsList())
            except Exception:
                logger.exception("unable to list system tactics for squad workspace")
        return tuple(
            sorted(
                (name for name in names if name.strip()),
                key=str.casefold,
            )
        )

    def _requiredRoleRows(self) -> tuple[tuple[str, str], ...]:
        assert self.model is not None
        if self.model.tacticName in {"No tactic selected", "No tactic assigned"}:
            return ()
        loader = getattr(self.window(), "tacticModelLoader", None)
        if loader is None:
            return ()
        try:
            loaded = loader.tacticLoad(self.model.tacticName)
        except Exception:
            logger.exception(
                "unable to load tactic slots for squad analysis tactic=%r",
                self.model.tacticName,
            )
            return ()
        tactic = getattr(loaded, "tactic", None)
        if tactic is None:
            return ()
        inPositions = tuple(tactic.inPossession.positions)
        outPositions = tuple(tactic.outOfPossession.positions)
        inIds = {position.slotId for position in inPositions if position.slotId}
        outIds = {position.slotId for position in outPositions if position.slotId}
        sharedIds = inIds.intersection(outIds)
        expectedShared = min(len(inPositions), len(outPositions))
        useSlotIds = expectedShared > 0 and len(sharedIds) == expectedShared
        roleByCode = {role.roleCode: role for role in self.model.roles}
        slots: dict[str, dict[str, object]] = {}
        order: list[str] = []
        for phase, positions in (("IP", inPositions), ("OOP", outPositions)):
            for index, position in enumerate(positions):
                key = (
                    str(position.slotId)
                    if useSlotIds and position.slotId
                    else f"ordinal:{index}"
                )
                if key not in slots:
                    slots[key] = {"position": "", "roles": []}
                    order.append(key)
                positionName = position.canonicalPosition or position.identity.value
                if not slots[key]["position"]:
                    slots[key]["position"] = positionName
                roleCode = position.canonicalRole
                role = roleByCode.get(roleCode) if roleCode else None
                roleLabel = (
                    role.abbreviation
                    if role is not None
                    else roleCode or position.roleProfile.name or "Unavailable"
                )
                coverage = (
                    role.coverage
                    if role is not None
                    else "Unavailable — role assessment is unresolved"
                )
                roles = slots[key]["roles"]
                if isinstance(roles, list):
                    roles.append((phase, roleLabel, coverage))
        rows: list[tuple[str, str]] = []
        for key in order:
            entry = slots[key]
            roleFacts = entry["roles"] if isinstance(entry["roles"], list) else []
            uniqueLabels = list(dict.fromkeys(fact[1] for fact in roleFacts))
            roleText = (
                uniqueLabels[0]
                if len(uniqueLabels) == 1
                else " / ".join(
                    f"{phase} {label}"
                    for phase, label, _coverage in roleFacts
                )
            )
            positionText = self._positionDisplay(str(entry["position"]))
            label = f"{roleText} · {positionText}" if positionText else roleText
            uniqueCoverage = list(dict.fromkeys(fact[2] for fact in roleFacts))
            coverageText = (
                uniqueCoverage[0]
                if len(uniqueCoverage) == 1
                else " | ".join(
                    f"{phase} {roleLabel}: {coverage}"
                    for phase, roleLabel, coverage in roleFacts
                )
            )
            rows.append((label, coverageText))
        if (
            self.model.requiredPositionCount
            and len(rows) != self.model.requiredPositionCount
        ):
            logger.warning(
                "squad analysis slot count mismatch tactic=%r expected=%d actual=%d",
                self.model.tacticName,
                self.model.requiredPositionCount,
                len(rows),
            )
        return tuple(rows)

    @staticmethod
    def _positionDisplay(position: str) -> str:
        direct = {
            "GK": "GK",
            "DL": "D(L)",
            "DC": "D(C)",
            "DR": "D(R)",
            "WBL": "WB(L)",
            "WBR": "WB(R)",
            "DM": "DM(C)",
            "ML": "M(L)",
            "MC": "M(C)",
            "MR": "M(R)",
            "AML": "AM(L)",
            "AMC": "AM(C)",
            "AMR": "AM(R)",
            "ST": "ST(C)",
            "STC": "ST(C)",
        }
        if position in direct:
            return direct[position]
        sideMap = {
            "DCL": "D(CL)",
            "DCR": "D(CR)",
            "DMCL": "DM(CL)",
            "DMCR": "DM(CR)",
            "MCL": "M(CL)",
            "MCR": "M(CR)",
            "AMCL": "AM(CL)",
            "AMCR": "AM(CR)",
            "STCL": "ST(CL)",
            "STCR": "ST(CR)",
        }
        return sideMap.get(position, position)

    @staticmethod
    def _factCardCreate(label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("factCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(2)
        labelWidget = QLabel(label)
        labelWidget.setObjectName("factLabel")
        valueWidget = QLabel(value)
        valueWidget.setObjectName("factValue")
        valueWidget.setWordWrap(True)
        layout.addWidget(labelWidget)
        layout.addWidget(valueWidget)
        return card

    @staticmethod
    def _layoutClear(layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            childLayout = item.layout()
            childWidget = item.widget()
            if childLayout is not None:
                SquadDetailView._layoutClear(childLayout)
                childLayout.deleteLater()
            if childWidget is not None:
                childWidget.deleteLater()
