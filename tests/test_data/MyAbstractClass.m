classdef (Abstract = true, Sealed) MyAbstractClass < MyHandleClass & MyClass
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
        function abc = MyAbstractClass(y)
            abc.y = y
        end
    end
end
