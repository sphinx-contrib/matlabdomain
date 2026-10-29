classdef BaseTable < handle
    % BaseTable - A base class.

    properties
        baseProp % A property defined on the base class.
    end

    methods
        function obj = BaseTable(x)
            % BaseTable - Base constructor.
        end

        function addRow(obj, val)
            % addRow - Add a row, defined on the base class.
        end
    end
end
