classdef First
    % The first class

    properties
        a % The property
    end

    methods
        function self = First(a)
            % Constructor for First
            self.a = a;
        end

        function method_inside_classdef(obj, b)
            % Method inside class definition
            obj.a = b;
        end
    end
end
