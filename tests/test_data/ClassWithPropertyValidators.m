classdef ClassWithPropertyValidators < handle
    properties
        % The location
        Location(1,3) double {mustBeReal, mustBeFinite}

        % The label
        Label(1,:) char {mustBeMember(Label,{'High','Medium','Low'})} = 'Low'

        % The state
        State(1,1) matlab.lang.OnOffSwitchState

        % The report level
        ReportLevel (1,1) string {mustBeMember(ReportLevel,["short","failed","full"])} = "full"
    end
end
