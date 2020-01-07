classdef MatlabClass
    %[a test matlab class]
	%
    %:param [nonexitant_argument]: None!
    
    properties
        Property1
    end
    
    methods
        function outputArg = method1(obj,inputArg)
            %[this is a test of a method]
			%
            %:param [inputArg]: An input argument
            %:return: 'this is a test
            outputArg = 'this is a test';
        end
    end
end

