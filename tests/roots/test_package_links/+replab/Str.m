classdef Str < handle
% Defines a 'str' default method and overloads 'disp'
    methods
        function disp(self)
            maxRows = replab.Settings.strMaxRows;
            maxColumns = replab.Settings.strMaxColumns;
            lines = replab.longStr(self, maxRows, maxColumns);
            lines = replab.str.longFit(lines, maxRows, maxColumns);
            disp(strjoin(lines, '\n'));
        end
    end
end
