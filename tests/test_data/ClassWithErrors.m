classdef ClassWithErrors
    % Class defintion with missing end

    methods
        function obj = ClassWithoutIndent()
            obj.a = 10;
    end
end