classdef ClassWithGetterSetter
    % Class with get and set methods for property access
    properties
        a  % A nice property
    end

    methods
        function ClassWithGetterSetter(obj)
            % Constructor
            disp('ClassWithGetterSetter');
        end

        function value = get.a(obj)
            % The getter method
            value = obj.a * 2;
        end

        function set.a(obj, value)
            % The setter method
            obj.a = value * 0.5;
        end

    end
end
