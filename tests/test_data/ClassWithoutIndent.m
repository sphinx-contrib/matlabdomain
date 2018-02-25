classdef ClassWithoutIndent
% First line is not indented
    % Second line line is indented

    % Indented, but not part of docstring
    properties
        a
    end

    methods
        function obj = ClassWithoutIndent()
            obj.a = 10;
        end
    end
end