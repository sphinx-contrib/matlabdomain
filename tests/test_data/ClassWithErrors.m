classdef ClassWithErrors
    % Class definition with missing end

    methods
        function obj = ClassWithoutIndent()
            obj.a = 10;
    end
end
