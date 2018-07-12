classdef ClassWithBuiltinOverload
    % Class that overloads a builtin

    methods
        function y = sin(obj, x)
            % overloading sin(x)
            y = builtin('sin', x);
        end

        function y = disp(obj)
            % Display object
            builtin('disp',p) % call builtin
        end
    end
end

