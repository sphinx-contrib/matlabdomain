classdef ClassBar < handle
% The Bar and Foo handler

    properties
        bars  % Number of bars

        % Number of foos
        foos
    end

    methods
        function obj = ClassBar()
            % Initialize the bars and foos
            obj.bars = "bars";
            obj.foos = "foos";
        end

        function doFoo(obj)
            % Doing foo
        end

        function doBar(obj)
            % Doing bar
        end
    end
end
