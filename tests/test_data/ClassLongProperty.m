classdef ClassLongProperty
    % test class property with long docstring
    %
    % :param a: the input to :class:`ClassExample`

    properties
		a  % short description

		% A property with a long documentation
		% This is the second line
		% And a third
		b % a property

        % This comment is not for property c

        c
    end
    methods
        function b = get.b(a)
			% Description of the property getter
			% This is not rendered to be consistent with Matlab
            b = 0;
        end
		end
end
