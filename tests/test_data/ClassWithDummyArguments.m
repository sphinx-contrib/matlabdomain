classdef ClassWithDummyArguments < handle
    methods
        function output = someMethod1(obj, argument)
            % Docstring
        end
        function output = someMethod2(~, argument)
            % Docstring
        end
    end
end