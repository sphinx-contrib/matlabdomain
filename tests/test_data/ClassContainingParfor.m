classdef ClassContainingParfor
    % Parfor is a keyword

    properties
        Property1
    end

    methods
        function obj = test(inputArg1,inputArg2)
            % A method with parfor
            obj.Property1 = inputArg1 + inputArg2;
            parfor i = 1:10
            end
        end
    end
end
