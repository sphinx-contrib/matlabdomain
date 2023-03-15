classdef ClassWithGetMethod < handle
    % Class with a method named get
    methods
        function varargout = get(self)
            % Gets the numbers 1-n and fills in the outputs with them
            %
            % Returns:
            %     double: multiple outputs with data `1` to `n` respectively.
            %
            for i=1:nargout
                varargout{i} = i;
            end
        end
    end
end
