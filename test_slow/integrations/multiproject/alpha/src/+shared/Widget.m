classdef Widget
    % WIDGET Alpha-only widget that holds a zorblax reading.

    properties
        Reading = 0  % Last zorblax reading
    end

    methods
        function obj = spin(obj)
            % SPIN Spin the widget (widgetspin).
            obj.Reading = -obj.Reading;
        end
    end
end
