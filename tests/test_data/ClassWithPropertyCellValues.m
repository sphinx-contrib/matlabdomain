classdef ClassWithPropertyCellValues
    % A class with property values initialized with a cell array.
    % The special thing is the two newlines in the midst of the cell array.


    properties
        fields = {
            'Level', [], @isnumeric
            'SingleValues','',                 @(x) isempty(x) || iscell(x) || ischar(x)



            % Multiple newlines in middle of default value.
            'Unit', '', @(x) ismember(x,{'mV','dBV','dBSPL','mA/m'})
            }

    end

    methods
        function obj = ClassWithPropertyCellValues()

        end

        function level = getLevel(obj)
            % Return the level
            level = obj.fields{1};
        end

        function level = getUnit(obj)
            % Return the unit
            level = obj.fields{3};
        end
    end
end
