classdef ClassExample < handle
    % Example class
    %
    % :param a: first property of :class:`ClassExample`
    % :param b: second property of :class:`ClassExample`

    properties
        a % a property
        b = 10 % a property with default value
    end
    methods
        function mc = ClassExample(a)
            mc.a = a;
        end

        function c = mymethod(obj, b)
        % A method in :class:`ClassExample`
        %
        % :param b: an input to :meth:`mymethod`
            for n = 1:10
                if n > 5
                    c = obj.a + b;
                else
                    c = obj.a + b^2;
                end
            end
        end
    end
end
