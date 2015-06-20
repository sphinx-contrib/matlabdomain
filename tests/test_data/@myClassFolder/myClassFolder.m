classdef myClassFolder
    % MYCLASSFOLDER

    properties
        p % a property of a class folder
        % comments on last line cause issues
    end

    methods
        function self = myClassFolder(p)
            self.p = p
        end
        % comments on last line cause issues
    end

    methods (Static)
        % skip comments above
        retv = my_static_func(args) % skip comments inline
        % not a real method, just testing brackets
        [a,b] = my_dumb_function(lots, ... ellipsis are treated as comments
            of, args)
        function_with_no_io  % not a real method, just another test
    end
end
