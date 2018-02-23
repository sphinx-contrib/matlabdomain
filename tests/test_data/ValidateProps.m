classdef ValidateProps
   properties
      % some comment before
      Location(1,3) double {mustBeReal, mustBeFinite} % docstring for Location
      Label(1,:) char {mustBeMember(Label,{'High','Medium','Low'})} = 'Low'
      State(1,1) matlab.lang.OnOffSwitchState
   end
end