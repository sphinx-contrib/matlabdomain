classdef DerivedTable < pkg.BaseTable
    % DerivedTable - A derived class.

    properties
        derivedProp % A property defined on the derived class.
    end

    methods
        function obj = DerivedTable(y)
            % DerivedTable - Derived constructor.
        end

        function ownMethod(obj)
            % ownMethod - A method defined on the derived class.
        end
    end
end
