classdef ClassWithStrings
    methods
        function obj = raiseError(obj)
            % Raises error with string
            errStr = "Hello World";
            error('ErrorID', errStr)
        end
    end
end