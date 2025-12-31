classdef YourClass
    % YourClass
    %
    % See Also: Myclass
    %

    properties
        % The property
        prop;
    end
    methods
        function obj = YourClass()
            % The YourClass constructor
            obj.prop = 10;
        end

        function obj = add(obj, value)
            % Add the value
            obj.prop = obj.prop + value;
        end
    end
end
