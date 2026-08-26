from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PlayerTraitIdentity(StrEnum):
    """Canonical identities for the Football Manager player traits."""

    runsWithBallDownLeft = "Runs With Ball Down Left"
    runsWithBallDownRight = "Runs With Ball Down Right"
    runsWithBallThroughTheCentre = "Runs With Ball Through The Centre"
    getsIntoOppositionArea = "Gets Into Opposition Area"
    movesIntoChannels = "Moves Into Channels"
    getsForwardWheneverPossible = "Gets Forward Whenever Possible"
    playsShortSimplePasses = "Plays Short Simple Passes"
    triesKillerBallsOften = "Tries Killer Balls Often"
    shootsFromDistance = "Shoots From Distance"
    shootsWithPower = "Shoots With Power"
    placesShots = "Places Shots"
    curlsBall = "Curls Ball"
    likesToRoundKeeper = "Likes To Round Keeper"
    likesToTryToBreakOffsideTrap = "Likes To Try To Break Offside Trap"
    arguesWithOfficials = "Argues With Officials"
    likesToLobKeeper = "Likes To Lob Keeper"
    playsNoThroughBalls = "Plays No Through Balls"
    dwellsOnBall = "Dwells On Ball"
    arrivesLateInOppositionArea = "Arrives Late In Opposition Area"
    triesToPlayWayOutOfTrouble = "Tries To Play Way Out Of Trouble"
    staysBackAtAllTimes = "Stays Back At All Times"
    divesIntoTackles = "Dives Into Tackles"
    doesNotDiveIntoTackles = "Does Not Dive Into Tackles"
    hitsFreeKicksWithPower = "Hits Free Kicks With Power"
    runsWithBallOften = "Runs With Ball Often"
    runsWithBallRarely = "Runs With Ball Rarely"
    triesLongRangeFreeKicks = "Tries Long Range Free Kicks"
    cutsInsideFromBothWings = "Cuts Inside From Both Wings"
    comesDeepToGetBall = "Comes Deep To Get Ball"
    hugsLine = "Hugs Line"
    looksForPassRatherThanAttemptingToScore = "Looks For Pass Rather Than Attempting To Score"
    marksOpponentTightly = "Marks Opponent Tightly"
    playsWithBackToGoal = "Plays With Back To Goal"
    possessesLongFlatThrow = "Possesses Long Flat Throw"
    stopsPlay = "Stops Play"
    triesFirstTimeShots = "Tries First Time Shots"
    playsOneTwos = "Plays One-Twos"
    dictatesTempo = "Dictates Tempo"
    attemptsOverheadKicks = "Attempts Overhead Kicks"
    knocksBallPastOpponent = "Knocks Ball Past Opponent"
    avoidsUsingWeakerFoot = "Avoids Using Weaker Foot"
    triesLongRangePasses = "Tries Long Range Passes"
    likesToSwitchBallToWideAreas = "Likes To Switch Ball To Wide Areas"
    penaltyBoxPlayer = "Penalty Box Player"
    usesLongThrowToStartCounterAttacks = "Uses Long Throw To Start Counter Attacks"
    refrainsFromTakingLongShots = "Refrains From Taking Long Shots"
    cutsInsideFromLeftWing = "Cuts Inside From Left Wing"
    cutsInsideFromRightWing = "Cuts Inside From Right Wing"
    likesBallPlayedIntoFeet = "Likes Ball Played Into Feet"
    crossesEarly = "Crosses Early"
    bringBallOutOfDefence = "Bring Ball Out of Defence"
    usesOutsideOfFoot = "Uses Outside Of Foot"
    windsUpOpponents = "Winds Up Opponents"
    movesBallToRightFootBeforeDribbleAttempt = "Moves Ball To Right Foot Before Dribble Attempt"
    movesBallToLeftFootBeforeDribbleAttempt = "Moves Ball To Left Foot Before Dribble Attempt"
    triesTricks = "Tries Tricks"
    getsCrowdGoing = "Gets Crowd Going"
    likesToBeatOpponentRepeatedly = "Likes To Beat Opponent Repeatedly"
    demandsToTakeFreeKicks = "Demands to Take Free Kicks"
    demandsToTakePenalties = "Demands to Take Penalties"
    playsBallWithFeet = "Plays Ball With Feet"


@dataclass(slots=True)
class Trait:
    """A Football Manager player trait."""

    name: str
    description: str = ""
    identity: PlayerTraitIdentity | None = None


# This catalogue represents the complete list visible in the supplied FM26
# player-trait selector. Checkbox states in the source images are ignored.
playerTraits = tuple(
    Trait(name=identity.value, identity=identity) for identity in PlayerTraitIdentity
)
