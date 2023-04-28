classdef ClassFolder
    % A class in a folder

    properties
        p % a property of a class folder
    end

    methods
        function self = ClassFolder(p)
            self.p = p
        end

        function method_inside_classdef(obj, a, b)
        % Method inside class definition
            a = b;
        end
    end

    methods (Static)
        % skip comments above
        retv = a_static_func(args) % skip comments inline
    end
end
