# Football Object Model

An Ada type package sepcification defining the football object model.

``` ada
-----------------------------------------------------------------------------
-- Football Object Model
--
-- Tactic
--
-- Represents a complete football tactic.
------------------------------------------------------------------------------

package Tactics is

    -- Model text as references to strings so record fields can vary in length.
    type Text;

    type Role_Identity is
    (
        BCB,
        DLP,
        CB,
        HB,
        WB,
        DM,
        CM,
        AM,
        W,
        CF
    );

    type Attribute is record
        Name : Text;
        Weighting : Integer;
    end record;

    type Attribute_List; -- of array of Attribute

    type Trait is record
        Name : Text;
        Description : Text;
    end record;

    type Trait_List; -- of array of Trait

    -- an Instruction has a title and then a number of selectors
    -- for example, Tempo has values 
    -- Much Lower, Lower, Standard, Higher, Much Higher

    type Instruction_Value_List; -- of array of Text 

    type Instruction is record
        Name : Text; -- eg. Tempo
        Values : Instruction_Value_List; -- eg. Much Lower, Lower, Standard, Higher, Much Higher
    end record;

    type Team_Instruction_List; -- of array of Instruction
    type Player_Instruction_List; -- of array of Instruction

    type Role is record
        Name : Role_Identity;
        Description : Text;
    end record;

    type Behaviour is record
        Name        : Text;
        Description : Text;
    end record;

    type BehaviourList; -- of array of Behaviour

    type Role_Profile is record
        Name              : Text;
        Description       : Text;
        Behaviours        : BehaviourList;
        Key_Attributes    : Attribute_List;
        Key_Traits        : Trait_List;
        Instructions      : Player_Instruction_List;
    end record;

    type Position_Needs_Type is record
        Name : Text;
        Description : Text;
    end record;

    type Position_Needs_List; -- of array of Position_Needs_Type

    type Position_Identity is
    (
        GK, DL, DC, DR,
        WBL, WBR, 
        DM,
        ML, MC, MR,
        AML, AMC, AMR,
        ST
    );

    type Position is record
        Identity : Position_Identity;
        Role : Role;
        Role_Profile : Role_Profile;
        Player_Instructions : Player_Instruction_List;
        Position_Needs : Position_Needs_List;
    end record;

    type Position_List; -- of array of Position

    type Formation is record
        Name : Text;
        Positions : Position_List;
        Team_Instructions : Team_Instruction_List;
    end record;

    type Transition is null record;

    type Tactic is record
        In_Possession : Formation;
        Out_Of_Possession : Formation;
        Transition : Transition;
    end record;

private

end Tactics;
```