classdef MyClass < handle
    % test class methods
    %
    % :param a: the input to :class:`MyClass`

    properties
        a % a property
    end
    methods
        function mc = MyClass(a)
            mc.a = a
        end
        function c = mymethod(obj, b)
        % a method in :class:`MyClass`
        %
        % :param b: an input to :meth:`mymethod`

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
