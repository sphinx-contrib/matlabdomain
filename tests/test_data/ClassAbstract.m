classdef (Abstract = true, Sealed) ClassAbstract < ClassInheritHandle & ClassExample
	% an abstract class
    %
	% :param y: a variable
    % :type y: double

    properties (Constant)
        version = '0.1.1-beta' % version
    end
    properties (SetAccess = private, GetAccess = private)
        %: one day this will work
        y % y variable
    end
    methods
        function abc = ClassAbstract(y)
            abc.y = y
        end
    end
end
