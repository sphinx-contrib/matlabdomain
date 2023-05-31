classdef FirstClass
    % First class with two properties

    properties
        a % The a property
        b % The b property
    end

    methods
        function obj = ClassSimple(a)

        end

        function c = method(obj, b)
            c = b * 2;
        end
    end
end
