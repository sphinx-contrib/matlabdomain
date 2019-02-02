classdef ClassWithDoubleQuotedString
    %WHATEVER Summary of this class goes here
    %   Detailed explanation goes here

    properties
        Property1
    end

    methods
        function obj = ClassWithDoubleQuotedString(inputArg1)
            %ClassWithDoubleQuotedString Construct an instance of this class
            %   Detailed explanation goes here

            blob = sprintf('%d', inputArg1);  % A comment with '%s'
            obj.Property1 = sprintf("%d", inputArg1);

        end

        function outputArg = method1(obj,inputArg)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            outputArg = obj.Property1 + inputArg;
        end
    end
end