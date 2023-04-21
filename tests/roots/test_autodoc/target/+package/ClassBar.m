classdef ClassBar < handle
% The Bar and Foo handler

    properties
        bars = 'bars' % Number of bars

        % Number of foos
        foos = 10
    end

    methods
        function obj = ClassBar()
            % Initialize the bars and foos
            obj.bars = 'bars';
            obj.foos = 42;
        end

        function doFoo(obj)
            % Doing foo
        end

        function doBar(obj)
            % Doing bar
        end
    end
end
