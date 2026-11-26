classdef Myclass
    % Myclass
    %
    % See Also: YourClass
    %

    properties
        % The property
        prop;
    end
    methods
        function obj = Myclass()
            % The Myclass constructor
            obj.prop = 10;
        end

        function obj = add(obj, value)
            % Add the value
            obj.prop = obj.prop + value;
        end
    end
end
