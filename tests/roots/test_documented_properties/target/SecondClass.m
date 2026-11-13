classdef SecondClass
    % Second class with methods and properties

    properties
        a % The a property
        b % The b property
    end

    methods
        function obj = SecondClass(a)
            % The second class constructor

        end

        function c = first_method(obj, b)
            c = b * 2;
        end

        function c = second_method(obj, b)
            c = b * 2;
        end
    end
end
