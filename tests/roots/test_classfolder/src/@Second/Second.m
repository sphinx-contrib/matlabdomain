classdef Second
    % The second class

    properties
        b % a property of a class folder
    end

    methods
        function self = Second(b)
            % Constructor for Second
            self.b = b;
        end

        function method_inside_classdef(obj, c)
            % Method inside class definition
            obj.b = c;
        end
    end
end
