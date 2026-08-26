"""Build a complete dummy tactic using the Football Object Model."""

from fmsat.football.instruction import Instruction, InstructionValue
from fmsat.football.role import Role
from fmsat.football.roleIdentity import RoleIdentity
from fmsat.football.roleProfile import RoleProfile
from fmsat.tactics.formation import Formation
from fmsat.tactics.position import Position
from fmsat.tactics.positionIdentity import PositionIdentity
from fmsat.tactics.tactic import Tactic
from fmsat.tactics.transition import Transition


def testBuildCompleteTactic() -> None:
    """A complete tactic can be constructed from reusable football objects."""

    # ------------------------------------------------------------------
    # Instruction values
    # ------------------------------------------------------------------

    standard = InstructionValue("Standard")

    stayWider = InstructionValue("Stay Wider")
    sitNarrower = InstructionValue("Sit Narrower")
    moveIntoChannels = InstructionValue("Move Into Channels")

    runWideWithBall = InstructionValue("Run Wider With The Ball")
    cutInsideWithBall = InstructionValue("Cut Inside With The Ball")

    holdPosition = InstructionValue("Hold Position")
    getFurtherForward = InstructionValue("Get Further Forward")

    counterPress = InstructionValue("Counter Press")
    regroup = InstructionValue("Regroup")

    counter = InstructionValue("Counter")
    holdShape = InstructionValue("Hold Shape")

    # ------------------------------------------------------------------
    # Instructions
    #
    # These objects describe the complete set of values available for each
    # instruction. The tactic selects one value from each set.
    # ------------------------------------------------------------------

    attackingWidth = Instruction(
        name="Attacking Width",
        values=(
            standard,
            stayWider,
            sitNarrower,
            moveIntoChannels,
        ),
    )

    dribblingDirection = Instruction(
        name="Dribbling Direction",
        values=(
            standard,
            runWideWithBall,
            cutInsideWithBall,
        ),
    )

    movement = Instruction(
        name="Movement",
        values=(
            standard,
            holdPosition,
            getFurtherForward,
        ),
    )

    possessionLost = Instruction(
        name="Possession Lost",
        values=(
            standard,
            counterPress,
            regroup,
        ),
    )

    possessionWon = Instruction(
        name="Possession Won",
        values=(
            standard,
            counter,
            holdShape,
        ),
    )

    # ------------------------------------------------------------------
    # Reusable Roles
    #
    # There is one object for each football role. The same Wing Back object,
    # for example, can be used by both left and right positions.
    # ------------------------------------------------------------------

    goalkeeper = Role(
        identity=RoleIdentity.GK,
        description="Protects the goal and starts possession.",
    )

    centreBack = Role(
        identity=RoleIdentity.CB,
        description="Defends central areas.",
    )

    ballPlayingDefender = Role(
        identity=RoleIdentity.BCB,
        description="Defends while contributing to progression from defence.",
    )

    halfBack = Role(
        identity=RoleIdentity.HB,
        description="Drops into the defensive line when required.",
    )

    deepLyingPlaymaker = Role(
        identity=RoleIdentity.DLP,
        description="Controls play from a deeper midfield position.",
    )

    wingBack = Role(
        identity=RoleIdentity.WB,
        description="Provides width and contributes in both directions.",
    )

    attackingMidfielder = Role(
        identity=RoleIdentity.AM,
        description="Links midfield and attack.",
    )

    winger = Role(
        identity=RoleIdentity.W,
        description="Provides attacking threat from wide areas.",
    )

    centreForward = Role(
        identity=RoleIdentity.CF,
        description="Leads the attack.",
    )

    # ------------------------------------------------------------------
    # Dummy role profiles
    #
    # These deliberately contain only enough data to exercise the model.
    # ------------------------------------------------------------------

    goalkeeperProfile = RoleProfile(
        name="Default",
        description="Default goalkeeper profile.",
    )

    centreBackProfile = RoleProfile(
        name="Default",
        description="Default central defender profile.",
    )

    ballPlayingProfile = RoleProfile(
        name="Default",
        description="Default ball-playing defender profile.",
    )

    halfBackProfile = RoleProfile(
        name="Default",
        description="Default Half Back profile.",
        instructions={
            movement: holdPosition,
        },
    )

    playmakerProfile = RoleProfile(
        name="Default",
        description="Default Deep-Lying Playmaker profile.",
    )

    wingBackProfile = RoleProfile(
        name="Default",
        description="Default Wing Back profile.",
    )

    attackingMidfielderProfile = RoleProfile(
        name="Default",
        description="Default Attacking Midfielder profile.",
    )

    wingerProfile = RoleProfile(
        name="Default",
        description="Default Winger profile.",
    )

    centreForwardProfile = RoleProfile(
        name="Default",
        description="Default Centre Forward profile.",
    )

    # ------------------------------------------------------------------
    # In Possession
    #
    # Dummy 3-2-4-1 shape.
    # ------------------------------------------------------------------

    inPossession = Formation(
        name="3-2-4-1",
        positions=[
            Position(
                identity=PositionIdentity.GK,
                role=goalkeeper,
                roleProfile=goalkeeperProfile,
            ),
            Position(
                identity=PositionIdentity.DC,
                role=centreBack,
                roleProfile=centreBackProfile,
            ),
            Position(
                identity=PositionIdentity.DC,
                role=ballPlayingDefender,
                roleProfile=ballPlayingProfile,
            ),
            Position(
                identity=PositionIdentity.DC,
                role=centreBack,
                roleProfile=centreBackProfile,
            ),
            Position(
                identity=PositionIdentity.DM,
                role=halfBack,
                roleProfile=halfBackProfile,
                instructions={
                    attackingWidth: sitNarrower,
                    movement: holdPosition,
                },
            ),
            Position(
                identity=PositionIdentity.DM,
                role=deepLyingPlaymaker,
                roleProfile=playmakerProfile,
            ),
            Position(
                identity=PositionIdentity.WBL,
                role=wingBack,
                roleProfile=wingBackProfile,
                instructions={
                    attackingWidth: stayWider,
                    dribblingDirection: runWideWithBall,
                },
            ),
            Position(
                identity=PositionIdentity.WBR,
                role=wingBack,
                roleProfile=wingBackProfile,
                instructions={
                    attackingWidth: stayWider,
                    dribblingDirection: runWideWithBall,
                },
            ),
            Position(
                identity=PositionIdentity.AML,
                role=winger,
                roleProfile=wingerProfile,
                instructions={
                    attackingWidth: sitNarrower,
                    dribblingDirection: cutInsideWithBall,
                },
            ),
            Position(
                identity=PositionIdentity.AMC,
                role=attackingMidfielder,
                roleProfile=attackingMidfielderProfile,
            ),
            Position(
                identity=PositionIdentity.ST,
                role=centreForward,
                roleProfile=centreForwardProfile,
            ),
        ],
        instructions={
            attackingWidth: stayWider,
        },
    )

    # ------------------------------------------------------------------
    # Out Of Possession
    #
    # Dummy 4-4-1-1 shape.
    # ------------------------------------------------------------------

    outOfPossession = Formation(
        name="4-4-1-1",
        positions=[
            Position(
                identity=PositionIdentity.GK,
                role=goalkeeper,
                roleProfile=goalkeeperProfile,
            ),
            Position(
                identity=PositionIdentity.DL,
                role=wingBack,
                roleProfile=wingBackProfile,
            ),
            Position(
                identity=PositionIdentity.DC,
                role=centreBack,
                roleProfile=centreBackProfile,
            ),
            Position(
                identity=PositionIdentity.DC,
                role=ballPlayingDefender,
                roleProfile=ballPlayingProfile,
            ),
            Position(
                identity=PositionIdentity.DR,
                role=wingBack,
                roleProfile=wingBackProfile,
            ),
            Position(
                identity=PositionIdentity.ML,
                role=winger,
                roleProfile=wingerProfile,
            ),
            Position(
                identity=PositionIdentity.MC,
                role=halfBack,
                roleProfile=halfBackProfile,
            ),
            Position(
                identity=PositionIdentity.MC,
                role=deepLyingPlaymaker,
                roleProfile=playmakerProfile,
            ),
            Position(
                identity=PositionIdentity.MR,
                role=winger,
                roleProfile=wingerProfile,
            ),
            Position(
                identity=PositionIdentity.AMC,
                role=attackingMidfielder,
                roleProfile=attackingMidfielderProfile,
            ),
            Position(
                identity=PositionIdentity.ST,
                role=centreForward,
                roleProfile=centreForwardProfile,
            ),
        ],
        instructions={},
    )

    # ------------------------------------------------------------------
    # Transition
    # ------------------------------------------------------------------

    transition = Transition(
        instructions={
            possessionLost: counterPress,
            possessionWon: counter,
        },
    )

    # ------------------------------------------------------------------
    # Complete tactic
    # ------------------------------------------------------------------

    libero = Tactic(
        name="Libero",
        inPossession=inPossession,
        outOfPossession=outOfPossession,
        transition=transition,
    )

    # ------------------------------------------------------------------
    # Basic model validation
    # ------------------------------------------------------------------

    assert len(libero.inPossession.positions) == 11
    assert len(libero.outOfPossession.positions) == 11

    assert libero.inPossession.name == "3-2-4-1"
    assert libero.outOfPossession.name == "4-4-1-1"

    # ------------------------------------------------------------------
    # Role reuse
    #
    # Both wing-back positions reference the same reusable Role object.
    # ------------------------------------------------------------------

    leftWingBack = libero.inPossession.positions[6]
    rightWingBack = libero.inPossession.positions[7]

    assert leftWingBack.role is wingBack
    assert rightWingBack.role is wingBack

    # ------------------------------------------------------------------
    # Instruction key/value model
    # ------------------------------------------------------------------

    assert leftWingBack.instructions[attackingWidth] == stayWider

    assert leftWingBack.instructions[dribblingDirection] == runWideWithBall

    halfBackPosition = libero.inPossession.positions[4]

    assert halfBackPosition.instructions[attackingWidth] == sitNarrower

    # ------------------------------------------------------------------
    # Role profile instructions and position instructions are independent.
    # ------------------------------------------------------------------

    assert halfBackProfile.instructions[movement] == holdPosition

    assert halfBackPosition.instructions[movement] == holdPosition

    # ------------------------------------------------------------------
    # Team instruction
    # ------------------------------------------------------------------

    assert libero.inPossession.instructions[attackingWidth] == stayWider

    # ------------------------------------------------------------------
    # Transition instructions use exactly the same model.
    # ------------------------------------------------------------------

    assert libero.transition.instructions[possessionLost] == counterPress

    assert libero.transition.instructions[possessionWon] == counter
