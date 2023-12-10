classdef NestedClassFolder
    % A class in a folder with functions in a sub-folder.

    properties
        p % The property
    end

    methods
        function self = ClassFolder(p)
            self.p = p
        end

        function y = method_calling_private(obj, x)
        % Method inside class definition
            y = private_function(x)
        end

        y = public_function(obj, x);
        % Method with implementation in file.
    end
end
