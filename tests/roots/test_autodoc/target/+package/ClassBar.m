classdef ClassBar < handle
% The Bar and Foo handler, with doFoo() and doBar() methods.

    properties
        bars = 'bars' % Number of bars

        % Number of foos, used by doBar() method
        foos = 10
    end

    methods
        function obj = ClassBar()
            % Initialize the bars and foos
            obj.bars = 'bars';
            obj.foos = 42;
        end

        function doFoo(obj)
            % doFoo - Doing foo, without passing in ``@ClassExample``
        end

        function doBar(obj)
            % Doing bar, not called by ClassBar()
        end
    end
end
