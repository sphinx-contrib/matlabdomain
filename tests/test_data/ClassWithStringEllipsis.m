classdef ClassWithStringEllipsis
    % Contains ellipsis in string

    properties
        Property1
    end

    methods
        function obj = test(inputArg1,inputArg2)
            %TEST Construct an instance of this class
            %
            %   Detailed explanation goes here
            fprintf("...");
            return;
        end
    end
end
