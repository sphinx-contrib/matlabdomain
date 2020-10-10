classdef ClassWithFunctionArguments < handle
    % test class methods with function arguments
    %
    % :param a: the input to :class:`ClassWithFunctionArguments`
    
    properties
        a % a property
    end
    methods
        function mc = ClassExample(a)
            arguments
                a
            end
            mc.a = a
        end
        function c = mymethod(obj, b)
        % a method in :class:`ClassWithFunctionArguments`
        %
        % :param b: an input to :meth:`mymethod`
            arguments
                obj
                b = 1
            end
            for n = 1:10
                if n > 5
                    c = obj.a + b
                else
                    c = obj.a + b^2
                end
            end
        end
        function c = nondocumentedmethod(obj, b)
            arguments
                obj
                b = 1
            end
            for n = 1:10
                if n > 5
                    c = obj.a + b
                else
                    c = obj.a + b^2
                end
            end
        end
    end
end
