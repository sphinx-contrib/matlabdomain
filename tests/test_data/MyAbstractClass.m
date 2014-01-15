classdef (Abstract = true, Sealed) MyAbstractClass
	% an abstract class with tabs
	% :param y: a variable
    % :type y: double

    properties (Constant)
        version = '0.1.1-beta' % version
    end
    properties (SetAccess = private, GetAccess = private)
        % one day this will work
        y % y variable
    end
end
