classdef Third
    % The third class

    properties
        c % a property of a class folder
    end

    methods
        function self = Third(c)
            % Constructor for Third
            self.c = c;
        end

        function method_inside_classdef(obj, d)
            % Method inside class definition
            obj.c = d;
        end
    end
end
